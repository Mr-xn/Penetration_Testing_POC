# AFL源码分析系列（三）-- afl-llvm-mode
> 有毒
> 来源：https://www.iotsec-zone.com/article/197

# llvm-mode

AFL 开发了 llvm-mode 来替代传统的 `afl-gcc/clang` 编译方式。常规的 `afl-gcc/clang` 模式是在汇编级别进行指令重写（包含新增和优化）来实现插桩，而 llvm-mode 是在编译器级别进行插桩，这有几个优势：

- 编译器可以进行许多在手动插入汇编时难以实现的优化，因此对于一些受CPU性能影响导致运行速度很慢的程序可以提升2倍左右的运行速度。但是这种速度上的提升在一些二进制文件时比较一般，大概只有10%左右的提升。
- 编译器级别的插桩是独立于CPU的。在原则上，可以利用这个特性在一些非x86的架构上去fuzz程序（需要设置环境变量AFL_NO_X86=1来编译afl-fuzz）。
- 这种插桩可以更好地应对多线程场景。
- llvm-mode 会以来 LLVM 的内核，所以这种模式是特定于 clang 的，不能和 GCC 一起使用。

# afl-clang-fast.c

## 1. 文件描述

该文件可以看作是 `clang` 的一个 wrapper ，在大多数的功能上与 `afl-gcc` 类似。在该文件中，会尝试确认编译模式，然后根据不同情况添加一些编译标志，最后去调用真正的编译器。

## 2. 文件架构

![0.png](https://www.iotsec-zone.com/images/MdImg/8ee995f034dbbfd2c58050c08f4ff222.png)

文件内部有3个函数：`main` 、`find_obj`、 `edit_params`，使用到的数据结构和变量基本都遇见过，包含的头文件也都见过，结构整体上还是比较简单的。

## 3. 源码分析

### 1. 部分关键变量

```c
static u8*  obj_path;               /* Path to runtime libraries         */
static u8** cc_params;              /* Parameters passed to the real CC  */
static u32  cc_par_cnt = 1;         /* Param count, including argv0      */
```

基本没有特殊的变量定义，`obj_path` 变量保存的是运行时库的路径。

### 2. main函数

```c
/* Main entry point */

int main(int argc, char** argv) {

  if (isatty(2) && !getenv("AFL_QUIET")) {

#ifdef USE_TRACE_PC
    SAYF(cCYA "afl-clang-fast [tpcg] " cBRI VERSION  cRST " by <lszekeres@google.com>\n");
#else
    SAYF(cCYA "afl-clang-fast " cBRI VERSION  cRST " by <lszekeres@google.com>\n");
#endif /* ^USE_TRACE_PC */

  }

  if (argc < 2) {
		... ...
  }

#ifndef __ANDROID__
  find_obj(argv[0]);
#endif

  edit_params(argc, argv);
  execvp(cc_params[0], (char**)cc_params);
  FATAL("Oops, failed to execute '%s' - check your PATH", cc_params[0]);
  return 0;
}
```

`main` 函数主要还是作为程序入口，核心功能由 `find_obj(argv[0])` 和 `edit_params(argc, argv)` 来完成，处理完路径和参数后，调用 `execvp(cc_params[0], (char**)cc_params)` 去执行。

>`main` 函数中有对 `USE_TRACE_PC` 宏的判断，这个宏表示的其实是 `AFL_TRACE_PC`这个环境变量。该变量来自于新版本的LLVM中的内置的执行跟踪的功能，利用这个功能，AFL 可以直接调用 LLVM 的跟踪数据，而无需再对汇编进行处理或者安装其他的编译器插件。如果设置了这个宏，表示使用 LLVM 内置的跟踪功能，如果没有，则使用常规的 AFL 自实现的llvm的pass：*afl-llvm-pass.so* 来进行插桩。该特性的详细内容可以参考 [http://clang.llvm.org/docs/SanitizerCoverage.html#tracing-pcs-with-guards](http://clang.llvm.org/docs/SanitizerCoverage.html#tracing-pcs-with-guards)。

### 3. find_obj函数

该函数主要是查找 runtime libraries 的路径：

```c
/* Try to find the runtime libraries. If that fails, abort. */

static void find_obj(u8* argv0) {

  u8 *afl_path = getenv("AFL_PATH");
  u8 *slash, *tmp;

  if (afl_path) {

    tmp = alloc_printf("%s/afl-llvm-rt.o", afl_path);

    if (!access(tmp, R_OK)) {
      obj_path = afl_path;
      ck_free(tmp);
      return;
    }
    ck_free(tmp);
  }

  slash = strrchr(argv0, '/');
  if (slash) {

    u8 *dir;
    *slash = 0;
    dir = ck_strdup(argv0);
    *slash = '/';

    tmp = alloc_printf("%s/afl-llvm-rt.o", dir);

    if (!access(tmp, R_OK)) {
      obj_path = dir;
      ck_free(tmp);
      return;
    }
    ck_free(tmp);
    ck_free(dir);
  }

  if (!access(AFL_PATH "/afl-llvm-rt.o", R_OK)) {
    obj_path = AFL_PATH;
    return;
  }
  FATAL("Unable to find 'afl-llvm-rt.o' or 'afl-llvm-pass.so'. Please set AFL_PATH");
}
```

1. 获取环境变量 `AFL_PATH` ，赋值给 `afl_path`。如果找到，拼接 `$afl_path/afl-llvm-rt.o` ，并确定可以访问，然后把该路径赋值给 `obj_path`；
2. 如果获取失败，找最后一个 `/` ，提取其 dir ，然后拼接成 `$dir/afl-llvm-rt.o` ，并确定可以访问，然后把该路径赋值给 `obj_path`。

`afl-llvm-rt.o` 由 `afl-llvm-rt.o.c` 编译获得，我们在后面会介绍该文件，这就是运行时库。

### 4. edit_params函数

该函数会根据各种不同的情况，添加不同的编译选项：

```c
/* Copy argv to cc_params, making the necessary edits. */

static void edit_params(u32 argc, char** argv) {

  u8 fortify_set = 0, asan_set = 0, x_set = 0, bit_mode = 0;
  u8 *name;

  cc_params = ck_alloc((argc + 128) * sizeof(u8*));

  name = strrchr(argv[0], '/');
  if (!name) name = argv[0]; else name++;
  if (!strcmp(name, "afl-clang-fast++")) {
    u8* alt_cxx = getenv("AFL_CXX");
    cc_params[0] = alt_cxx ? alt_cxx : (u8*)"clang++";
  } else {
    u8* alt_cc = getenv("AFL_CC");
    cc_params[0] = alt_cc ? alt_cc : (u8*)"clang";
  }

  /* There are two ways to compile afl-clang-fast. In the traditional mode, we
     use afl-llvm-pass.so to inject instrumentation. In the experimental
     'trace-pc-guard' mode, we use native LLVM instrumentation callbacks
     instead. The latter is a very recent addition - see:

     http://clang.llvm.org/docs/SanitizerCoverage.html#tracing-pcs-with-guards */

#ifdef USE_TRACE_PC
  cc_params[cc_par_cnt++] = "-fsanitize-coverage=trace-pc-guard";
	... ...
#else
  cc_params[cc_par_cnt++] = "-Xclang";
  cc_params[cc_par_cnt++] = "-load";
  cc_params[cc_par_cnt++] = "-Xclang";
  cc_params[cc_par_cnt++] = alloc_printf("%s/afl-llvm-pass.so", obj_path);
#endif /* ^USE_TRACE_PC */

  cc_params[cc_par_cnt++] = "-Qunused-arguments";

  while (--argc) {
    u8* cur = *(++argv);

    if (!strcmp(cur, "-m32")) bit_mode = 32;
    if (!strcmp(cur, "armv7a-linux-androideabi")) bit_mode = 32;
    if (!strcmp(cur, "-m64")) bit_mode = 64;
    if (!strcmp(cur, "-x")) x_set = 1;
    if (!strcmp(cur, "-fsanitize=address") ||
        !strcmp(cur, "-fsanitize=memory")) asan_set = 1;
    if (strstr(cur, "FORTIFY_SOURCE")) fortify_set = 1;
    if (!strcmp(cur, "-Wl,-z,defs") ||
        !strcmp(cur, "-Wl,--no-undefined")) continue;

    cc_params[cc_par_cnt++] = cur;
  }

  if (getenv("AFL_HARDEN")) {

    cc_params[cc_par_cnt++] = "-fstack-protector-all";
    if (!fortify_set)
      cc_params[cc_par_cnt++] = "-D_FORTIFY_SOURCE=2";
  }

  if (!asan_set) {
    if (getenv("AFL_USE_ASAN")) {
      if (getenv("AFL_USE_MSAN"))
        FATAL("ASAN and MSAN are mutually exclusive");
      if (getenv("AFL_HARDEN"))
        FATAL("ASAN and AFL_HARDEN are mutually exclusive");
      cc_params[cc_par_cnt++] = "-U_FORTIFY_SOURCE";
      cc_params[cc_par_cnt++] = "-fsanitize=address";
    } else if (getenv("AFL_USE_MSAN")) {
      if (getenv("AFL_USE_ASAN"))
        FATAL("ASAN and MSAN are mutually exclusive");
      if (getenv("AFL_HARDEN"))
        FATAL("MSAN and AFL_HARDEN are mutually exclusive");
      cc_params[cc_par_cnt++] = "-U_FORTIFY_SOURCE";
      cc_params[cc_par_cnt++] = "-fsanitize=memory";
    }
  }
#ifdef USE_TRACE_PC
  if (getenv("AFL_INST_RATIO"))
    FATAL("AFL_INST_RATIO not available at compile time with 'trace-pc'.");
#endif /* USE_TRACE_PC */

  if (!getenv("AFL_DONT_OPTIMIZE")) {
    cc_params[cc_par_cnt++] = "-g";
    cc_params[cc_par_cnt++] = "-O3";
    cc_params[cc_par_cnt++] = "-funroll-loops";
  }
  if (getenv("AFL_NO_BUILTIN")) {
    cc_params[cc_par_cnt++] = "-fno-builtin-strcmp";
    cc_params[cc_par_cnt++] = "-fno-builtin-strncmp";
    cc_params[cc_par_cnt++] = "-fno-builtin-strcasecmp";
    cc_params[cc_par_cnt++] = "-fno-builtin-strcasecmp";
    cc_params[cc_par_cnt++] = "-fno-builtin-memcmp";
  }
  cc_params[cc_par_cnt++] = "-D__AFL_HAVE_MANUAL_CONTROL=1";
  cc_params[cc_par_cnt++] = "-D__AFL_COMPILER=1";
  cc_params[cc_par_cnt++] = "-DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION=1";
  cc_params[cc_par_cnt++] = "-D__AFL_LOOP(_A)="
    "({ static volatile char *_B __attribute__((used)); "
    " _B = (char*)\"" PERSIST_SIG "\"; "
	... ...
    "_L(_A); })";
  cc_params[cc_par_cnt++] = "-D__AFL_INIT()="
    "do { static volatile char *_A __attribute__((used)); "
    " _A = (char*)\"" DEFER_SIG "\"; "
	... ...
    "_I(); } while (0)";

  if (x_set) {
    cc_params[cc_par_cnt++] = "-x";
    cc_params[cc_par_cnt++] = "none";
  }
	... ...
  cc_params[cc_par_cnt] = NULL;
}
```

1. 分配 `cc_params` 使用的内存：`ck_alloc((argc + 128) * sizeof(u8*))`，然后去提取 `argv[0]` ；
2. 如果是 `afl-clang-fast++` ，则获取 `AFL_CXX` 编译器，有则直接赋值，没有直接使用 `clang++`；如果是其他值，则获取 `AFL_CC` ，有则直接复制，没有直接使用 `clang`；
3. 判断是否开启宏 `USE_TRACE_PC`，如果开启，添加参数 `-fsanitize-coverage=trace-pc-guard -Qunused-arguments` 到 `cc_params` ；如果没有开启则添加 ` -Xclang -load -Xclang $afl_path/afl-llvm-pass.so -Qunused-arguments` ；
4. `while(--argc)` 循环来处理每个参数：
   1. 如果有 `-m32` 或 `armv7a-linux-androideabi` ，设置 `bit_mode = 32`， 表示32位程序；如果是 `-m64` ，则设置 `bit_mode=64`，表示64位程序；
   2. 如果有 `-x` ，设置 `x_set=1`；
   3. 如果有 `-fsanitize=address/memory`，则设置 `asan_set=1`，表示启用 ASan 的错误检测；
   4. 如果有 `FORTIFY_SOURCE`， 则设置 `fortify_set=1`，表示开启 Fortify；
   5. 如果有 `-Wl,-z,defs` 或者 `-Wl,--no-undefined`，直接进入下一个参数；
   6. 把每个参数放入 `cc_params` 数组。
5. 获取环境变量 `AFL_HARDEN` ，如果存在， 添加参数 `-fstack-protector-all`；如果没有设置 `fortify_set`， 则添加 `-D_FORTIFY_SOURCE=2`；
6. 接下来是内存检测的判断，如果没有设置 `asan_set`，则获取环境变量 `AFL_USE_ASAN` ，且不存在 `AFL_USE_MSAN` 及`AFL_HARDEN` 的情况下，添加参数 `-U_FORTIFY_SOURCE -fsanitize=address`；如果获取失败，则尝试获取 `AFL_USE_MSAN` ，并添加参数 `-U_FORTIFY_SOURCE -fsanitize=memory`；
7. 然后是插桩密度的设置：
   1. 如果定义了 `USE_TRACE_PC` 宏，表示使用 LLVM 内置功能，所以此时不能同时设置 `AFL_INST_RATIO` 变量来设置插桩密度；
8. 获取 `AFL_DONT_OPTIMIZE` 变量，没有设置该变量表示可以进行编译优化，添加参数 `-g -O3 -funroll-loops`；
9. 获取 `AFL_NO_BUILTIN`变量，进行了设置则追加 `-fno-builtin-strcmp` 等cmp类型的参数；
10. 最后追加 `-D__AFL_HAVE_MANUAL_CONTROL=1 -D__AFL_COMPILER=1 -DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION=1`；
11. 接下来是关于 `persistent mode` 相关的设置（该模式我们会在 `afl-fuzz.c` 的分析中再展开解释）：设置宏 `__AFL_LOOP(_A) `和 宏 `__AFL_INIT()` ；
12. 检查是否设置了 `x_set` ，如果设置则追加 `-x none` 参数。

该文件中对参数的处理逻辑整体上跟 `afl-gcc.c` 中的是一致的，只是根据不同的编译场景和选择在编译相关的参数方面会选择添加不同的编译选项。

# afl-llvm-pass.so.cc

## 1. 文件描述

该文件实现了 LLVM-mode 下的一个插桩 LLVM Pass，当通过 `afl-clang-fast` 调用 clang 时，该 pass 会被插入到 LLVM 中，告诉编译器需要添加与 `afl-as.h` 中逻辑类似的桩代码。

## 2. 文件架构

文件内部定义了一个 `AFLCoverage` 类，然后实现了一个 `runOnModule()` 函数，该函数完成核心的插桩工作。pass 的注册由 `registerAFLPass()` 函数完成。

![1.png](https://www.iotsec-zone.com/images/MdImg/cb53a41d2380a188e10b8c80c9334637.png)

## 3. 源码分析

对于 llvm pass 的注册部分我们不做关心，只关注实现插桩的 `runOnModule()` 函数。

文件中只有一个 pass：

```c++
namespace {

  class AFLCoverage : public ModulePass {

    public:

      static char ID;
      AFLCoverage() : ModulePass(ID) { }

      bool runOnModule(Module &M) override;

      // StringRef getPassName() const override {
      //  return "American Fuzzy Lop Instrumentation";
      // }
  };
}
```

该 Pass 会完成插桩的操作。

### runOnModule函数

```c++
bool AFLCoverage::runOnModule(Module &M) {

  LLVMContext &C = M.getContext();

  IntegerType *Int8Ty  = IntegerType::getInt8Ty(C);
  IntegerType *Int32Ty = IntegerType::getInt32Ty(C);

  /* Show a banner */

  char be_quiet = 0;
  if (isatty(2) && !getenv("AFL_QUIET")) {
    SAYF(cCYA "afl-llvm-pass " cBRI VERSION cRST " by <lszekeres@google.com>\n");
  } else be_quiet = 1;

  /* Decide instrumentation ratio */

  char* inst_ratio_str = getenv("AFL_INST_RATIO");
  unsigned int inst_ratio = 100;

  if (inst_ratio_str) {
    if (sscanf(inst_ratio_str, "%u", &inst_ratio) != 1 || !inst_ratio ||
        inst_ratio > 100)
      FATAL("Bad value of AFL_INST_RATIO (must be between 1 and 100)");
  }

  /* Get globals for the SHM region and the previous location. Note that
     __afl_prev_loc is thread-local. */

  GlobalVariable *AFLMapPtr =
      new GlobalVariable(M, PointerType::get(Int8Ty, 0), false,
                         GlobalValue::ExternalLinkage, 0, "__afl_area_ptr");

  GlobalVariable *AFLPrevLoc = new GlobalVariable(
      M, Int32Ty, false, GlobalValue::ExternalLinkage, 0, "__afl_prev_loc",
      0, GlobalVariable::GeneralDynamicTLSModel, 0, false);

  /* Instrument all the things! */

  int inst_blocks = 0;
  for (auto &F : M)
    for (auto &BB : F) {
      BasicBlock::iterator IP = BB.getFirstInsertionPt();
      IRBuilder<> IRB(&(*IP));

      if (AFL_R(100) >= inst_ratio) continue;

      /* Make up cur_loc */

      unsigned int cur_loc = AFL_R(MAP_SIZE);
      ConstantInt *CurLoc = ConstantInt::get(Int32Ty, cur_loc);

      /* Load prev_loc */

      LoadInst *PrevLoc = IRB.CreateLoad(AFLPrevLoc);
      PrevLoc->setMetadata(M.getMDKindID("nosanitize"), MDNode::get(C, None));
      Value *PrevLocCasted = IRB.CreateZExt(PrevLoc, IRB.getInt32Ty());

      /* Load SHM pointer */

      LoadInst *MapPtr = IRB.CreateLoad(AFLMapPtr);
      MapPtr->setMetadata(M.getMDKindID("nosanitize"), MDNode::get(C, None));
      Value *MapPtrIdx =
          IRB.CreateGEP(MapPtr, IRB.CreateXor(PrevLocCasted, CurLoc));

      /* Update bitmap */

      LoadInst *Counter = IRB.CreateLoad(MapPtrIdx);
      Counter->setMetadata(M.getMDKindID("nosanitize"), MDNode::get(C, None));
      Value *Incr = IRB.CreateAdd(Counter, ConstantInt::get(Int8Ty, 1));
      IRB.CreateStore(Incr, MapPtrIdx)
          ->setMetadata(M.getMDKindID("nosanitize"), MDNode::get(C, None));

      /* Set prev_loc to cur_loc >> 1 */

      StoreInst *Store =
          IRB.CreateStore(ConstantInt::get(Int32Ty, cur_loc >> 1), AFLPrevLoc);
      Store->setMetadata(M.getMDKindID("nosanitize"), MDNode::get(C, None));
      inst_blocks++;
    }

  /* Say something nice. */

  if (!be_quiet) {
    if (!inst_blocks) WARNF("No instrumentation targets found.");
    else OKF("Instrumented %u locations (%s mode, ratio %u%%).",
             inst_blocks, getenv("AFL_HARDEN") ? "hardened" :
             ((getenv("AFL_USE_ASAN") || getenv("AFL_USE_MSAN")) ?
              "ASAN/MSAN" : "non-hardened"), inst_ratio);
  }
  return true;
}
```

1. 调用 `Module::getContext()` 来获取 LLVMContext，进程上下文；
2. 获取环境变量 `AFL_INST_RATIO` 赋值给 `inst_ratio_str` ，插桩密度，并对其范围进行校验(1~100)；
3. 获取共享内存地址 `AFLMapPtr` 以及上一个位置的值 `AFLPrevLoc`；
4. 使用 `for` 循环进行插桩：
   1. 遍历每个基本块，寻找BB中适合插入桩代码的位置，然后初始化 `IRBuilder` 实例执行插入工作；
   2. 如果插桩密度大于等于 `inst_ratio` ，跳出本次循环；
   3. 设置当前位置 `cur_loc = AFL_R(MAP_SIZE)`，并转换成Int类型作为位置ID；
   4. 通过 `AFLPrevLoc` 获取前一个位置的ID - `PrevLoc`；
   5. 插入 `load` 指令，通过 `AFLMapPtr` 获取共享内存地址 - `MapPtr`，进行计算获取索引：`Value *MapPtrIdx = IRB.CreateGEP(MapPtr, IRB.CreateXor(PrevLocCasted, CurLoc))`，这里的计算方式还是使用的异或；
   6. 更新 bitmap ，插入 `load` 指令，获取对应 index地址的值；插入 `add` 指令加一，然后创建 `store` 指令写入新值，并更新共享内存；
   7. 设置 `prev_loc to cur_loc >> 1` ，插入 `store` 指令，更新 `__afl_prev_loc`；
   8. 插桩计数 + 1；
   9. 扫描下一个BB，根据设置是否为quiet模式等，并判断 `inst_blocks` 是否为0，如果为0则说明没有进行插桩。

至此为止，通过 LLVM Pass 进行插桩的过程就已经完成。LLVM 的插桩是修改的 IR ，我们会在 AFL 的深入使用中再进行深度介绍。

# afl-llvm-rt.o.c

## 1. 文件描述

该文件是运行时库文件，重写了 `afl-as.h` 文件中的 `main_payload` 部分，实现了 llvm-mode 的3个特殊功能：`deferred instrumentation`、`persistent mode`、`trace-pc-guard mode`。

### 1. deferred instrumentation

AFL 会只执行一次目标二进制，然后在 `main()` 函数之前停下。然后去克隆当前进程（master进程）来进行fuzz。本质上是一种快照机制，这样避免多次运行程序，提升效率。

虽然这种机制可以减少程序运行在操作系统、链接器和libc级别的消耗，但是在面对大型配置文件的解析时，优势并不明显。为了解决这个问题，AFL 可以借助 LLVM 将 forkserver 的初始化延后，放在其他大部分初始化工作完成之后、二进制文件获取fuzz输入之前的位置，这在某些情况下可以提升大约10倍的性能。

首先，在代码中找一个地方存放进行延迟克隆的代码的位置，这些位置有如下要求

- 不能是任何创建虚拟线程或子进程的地方，forkserver 无法进行clone
- 不能通过 `setitimer()` 或者类似的函数调用进行初始化的地方
- 不能是任何访问 fuzz 输入的地方

然后，添加如下代码：

```c
#ifdef __AFL_HAVE_MANUAL_CONTROL
  __AFL_INIT();
#endif
```

这个宏我们在 `afl-clang-fast` 中进行了定义。

最后，使用 `afl-clang-fast` 进行编译即可。

### 2. persistent mode

一些库会提供无状态或者状态在处理不同的输入文件时可以进行重置的API，遇到这种重置的情况时，可以重用一个长期存活的进程来尝试多个测试用例，从而消除反复 fork 造成的开销。

用代码表示这种思路如下所示：

```c
while (__AFL_LOOP(1000)) {

  /* Read input data. */
  /* Call library code to be fuzzed. */
  /* Reset state. */

}

/* Exit normally */
```

设置一个while循环，指定循环次数，在循环内部，读入数据 -> 执行 fuzz -> 重置状态，这样就可以在一个进程生命周期内完成 fuzz 过程，本质上也可以看作是一种快照，只不过是更细粒度的一种快照。

`__AFL_LOOP`这个宏我们在 `afl-clang-fast` 中进行了定义，循环次数这里作者建议给到1000次，如果次数过高，可能会发生内存泄漏。

需要注意的是，在使用该模式时，需要确保程序状态可以得到完善的重置，否则可能产生很多意料之外的错误，这就要求对目标程序的代码理解需要深入一些。

在性能上比不上 libfuzzer ，但是会比 fork 机制快很多。

### 3. 'trace-pc-guard' mode

这种模式我们在前面已经有介绍，使用方法是在构建 `afl-clang-fast` 时指定 `AFL_TRACE_PC=1`。这种模式的好处是不要使用单独开发的 pass ，直接使用 LLVM 内置的功能。但是在性能上会比常规 `afl-clang-fast` 和 `afl-clang` 差一点。

## 2. 文件架构 

文件包含的主要函数如下：

![2.png](https://www.iotsec-zone.com/images/MdImg/8bdc9e6afdfc1f9f944390c1365aa029.png)

## 3. 源码分析

### 1. deferred instrumentation

该模式下会在代码中添加如下code：

```c
#ifdef __AFL_HAVE_MANUAL_CONTROL
  __AFL_INIT();
#endif
```

而在 `__AFL_INIT()` 函数中，会调用 `__afl_manual_init` 函数，该函数源码如下：

```c
void __afl_manual_init(void) {

  static u8 init_done;

  if (!init_done) {

    __afl_map_shm();
    __afl_start_forkserver();
    init_done = 1;

  }
}
```

函数内部调用了 `__afl_map_shm()` 和 `__afl_start_forkserver()` 两个函数，判断逻辑是一个 `init_done` 变量，该变量表示了共享内存是否进行了初始化。如果没有，才会调用这两个函数。
`__afl_map_shm()` 函数代码：

```c
/* SHM setup. */

static void __afl_map_shm(void) {

  u8 *id_str = getenv(SHM_ENV_VAR);

  /* If we're running under AFL, attach to the appropriate region, replacing the
     early-stage __afl_area_initial region that is needed to allow some really
     hacky .init code to work correctly in projects such as OpenSSL. */

  if (id_str) {

    u32 shm_id = atoi(id_str);

    __afl_area_ptr = shmat(shm_id, NULL, 0);

    /* Whooooops. */

    if (__afl_area_ptr == (void *)-1) _exit(1);

    /* Write something into the bitmap so that even with low AFL_INST_RATIO,
       our parent doesn't give up on us. */

    __afl_area_ptr[0] = 1;

  }

}
```

该函数的主要工作是进行共享内存的设置，首先读取环境变量 `SHM_ENV_VAR` 来获取共享内存，然后使用 `shmat` 赋值给 `__afl_area_ptr` 。

接下来是 `__afl_start_forkserver()` 函数，该函数的负责的是 forkserver 的配置工作，其代码如下：

```c
static void __afl_start_forkserver(void) {

  static u8 tmp[4];
  s32 child_pid;

  u8  child_stopped = 0;

  /* Phone home and tell the parent that we're OK. If parent isn't there,
     assume we're not running in forkserver mode and just execute program. */

  if (write(FORKSRV_FD + 1, tmp, 4) != 4) return;   // 向状态管道写入4字节，表示已准备好

  while (1) {       // 进入死循环

    u32 was_killed;
    int status;

    /* Wait for parent by reading from the pipe. Abort if read fails. */

    if (read(FORKSRV_FD, &was_killed, 4) != 4) _exit(1);    // 读取控制管道的4字节，读取失败的话，发生阻塞
                                                            // 读取成功了，表示forkserver需要进行一次fuzz执行

    /* If we stopped the child in persistent mode, but there was a race
       condition and afl-fuzz already issued SIGKILL, write off the old
       process. */

    if (child_stopped && was_killed) {                      // 如果子进程停止了或者被kill了，设置child_stopped=0，并通过waitpid等待子进程执行完毕
      child_stopped = 0;
      if (waitpid(child_pid, &status, 0) < 0) _exit(1);     // 如果等待子进程发生错误，阻塞
    }

    if (!child_stopped) {                                   // 如果没有子进程，则直接fork一个子进程去执行fuzz

      /* Once woken up, create a clone of our process. */

      child_pid = fork();                                   // 如果没有子进程在，就fork一个
      if (child_pid < 0) _exit(1);

      /* In child process: close fds, resume execution. */

      if (!child_pid) {

        close(FORKSRV_FD);                                  // 关闭子进程的状态管道和控制管道
        close(FORKSRV_FD + 1);
        return;
      }
    } else {                                                // 如果存在子进程，则kill掉，进行重启

      /* Special handling for persistent mode: if the child is alive but
         currently stopped, simply restart it with SIGCONT. */

      kill(child_pid, SIGCONT);
      child_stopped = 0;
    }

    /* In parent process: write PID to pipe, then wait for child. */

    if (write(FORKSRV_FD + 1, &child_pid, 4) != 4) _exit(1);               // 将子进程id写入状态管道
    if (waitpid(child_pid, &status, is_persistent ? WUNTRACED : 0) < 0)    // 等待子进程执行结束
      _exit(1);

    /* In persistent mode, the child stops itself with SIGSTOP to indicate
       a successful run. In this case, we want to wake it up without forking
       again. */

    if (WIFSTOPPED(status)) child_stopped = 1;

    /* Relay wait status to pipe, then loop back. */

    if (write(FORKSRV_FD + 1, &status, 4) != 4) _exit(1);   // 子进程执行结束，向状态管道写入4字节，表示本次fuzz执行结束。
  }
}
```

1. 首先设置 `child_stopped` 变量为0，该变量来描述子进程的状态；
2. 向状态管道写入 4 字节，告知 fuzzer 已经准备好；
3. 进入 while 循环，这里本质上就是 fuzz 的 loop：
   1. 读取控制管道的 4 字节数据，读取成功表示需要执行一次 fuzz ，失败表示阻塞，退出；
   2. 判断 `child_stopped` 和 `was_killed` 状态，如果子进程停止了或者被kill了，设置child_stopped=0，并通过waitpid等待子进程执行完毕；如果等待过程出错，退出；
   3. 判断 `child_stopped`
      1. 如果为0，表示没有子进程，调用 fork 启动一个子进程，并获取 pid 。此时子进程会关闭状态管道和控制管道，然后执行 return， 跳出循环，恢复正常执行；
      2. 如果为 1，表示子进程还在，只是被暂停了，所以通过 `kill(child_pid, SIGCONT)` 的方式来重启，并设置 `child_stopped` 为0。需要注意的是，这里是对 persistent mode 的特殊处理；
   4. 在父进程中，向状态管道写入 4 字节数据，然后等待子进程执行结束。对于 persistent mode 下，waitpid 还会设置第三个参数为 `WUNTRACED` ，表示如果子进程进入暂停状态，立刻返回；
   5. `WIFSTOPPED(status)` 宏确定返回值是否对应于一个暂停子进程，因为在 persistent mode 下，子进程会通过 `SIGSTOP` 来暂停自己，并以此指示运行成功，所以在这种情况下，我们需要再进行一次fuzz，就只需要和上面一样，通过 `SIGCONT` 唤醒子进程继续执行即可，不需要再进行一次fuzz。设置 `child_stopped` 为 1；
   6. 子进程执行结束后，向状态管道写入 4 字节，通知 afl 本次 fuzz 执行结束。

### 2. persistent mode

前面有介绍过该模式，该模式的应用场景主要是一些库会提供无状态或者状态在处理不同的输入文件时可以进行重置的API，遇到这种重置的情况时，可以重用一个长期存活的进程来尝试多个测试用例，消除反复 fork 造成的开销。

用代码表示这种思路如下所示：

```c
while (__AFL_LOOP(1000)) {

  /* Read input data. */
  /* Call library code to be fuzzed. */
  /* Reset state. */

}

/* Exit normally */
```

这里的循环次数不能为了方便就设置过大，过大的循环次数可能会发生一些类似内存泄漏的问题，官方给出的指导阈值是 1000 。

这里会调用 `__afl_persistent_loop` 函数，该函数代码如下：

```c
int __afl_persistent_loop(unsigned int max_cnt) {

  static u8  first_pass = 1;
  static u32 cycle_cnt;

  if (first_pass) {         // 第一次执行

    if (is_persistent) {    // 如果是 persistent mode

      memset(__afl_area_ptr, 0, MAP_SIZE);  // 初始化__af_area_ptr处的内存
      __afl_area_ptr[0] = 1;
      __afl_prev_loc = 0;
    }

    cycle_cnt  = max_cnt;   
    first_pass = 0;
    return 1;
  }

  if (is_persistent) {      // 如果是 persistent mode
    if (--cycle_cnt) {      // 需要执行的循环数 - 1

      raise(SIGSTOP);       // 抛出 SIGSTOP 暂停当前进程

      __afl_area_ptr[0] = 1;
      __afl_prev_loc = 0;

      return 1;
    } else {

      __afl_area_ptr = __afl_area_initial; // 指向无关数组

    }
  }
  return 0;
}
```

函数本身其实比较简单：

1. 首先判断是不是第一次执行，如果是，再判断是否为 persistent mode，如果是，则初始化 `__afl_area_ptr` 指向的共享内存
1. 如果是第一次执行，还会设置 `cycle_cnt` 的值为传入参数 `max_cnt`，然后将 `first_pass` 设置为0，下次再进来就不是第一次执行了；
1. 如果是 persistent mode，首先将循环次数 -1，然后抛出 `SIGSTOP` 信号暂停当前进程，并设置 `__afl_area_ptr[0]=1`，`__afl_prev_loc = 0`。
1. 如果不是 persistent mode ，则设置 `__afl_area_ptr` 为一个无关数组。

这里向弄清楚 persistent mode 的运作机制，还需要了解一个函数 `__afl_auto_init`，其代码如下：

```c
/* Proper initialization routine. */

__attribute__((constructor(CONST_PRIO))) void __afl_auto_init(void) {

  is_persistent = !!getenv(PERSIST_ENV_VAR);

  if (getenv(DEFER_ENV_VAR)) return;

  __afl_manua l_init();

}
```

该函数会执行 persistent mode 的初始化工作，而且这里使用了 `__attribute__(constructor)` 来进行修饰，表明该函数会在 main 函数之前执行。

1. 函数首先判断 `PERSIST_ENV_VAR` 环境变量来确定是否处于 persistent mode，赋值给 `is_persistent` 变量；
2. 获取环境变量 `DEFER_ENV_VAR` 环境变量，如果成功获取，表明使用 deferred instrumentation 。我们在前面介绍这种模式时，它的初始化是自己选择时机进行手动初始化，而不是调用该函数，所以这两种模式的初始化不是同样的方法。
3. 最后调用 `__afl_manual_init` 函数来执行实际的初始化操作。

我们以一个实际的例子来说明 persistent mode 的运作过程。假设开发fuzzer的代码如下：

```c
... ...
  while (__AFL_LOOP(1000)){
    fuzzFunc();
  }
... ...
```

1. 在main函数之前，首先去执行 `__afl_auto_init(void)` 来进行初始化，主要是通过 `__afl_map_shm` 进行共享内存的读取和设置，通过 `__afl_fork_server` 来将当前进程设置为 fork server 和 fuzz 进行通信；

2. afl 发起 fuzz 通知，此时的 `child_stopped` 变量值为0， 所以进行 fork 一个子进程；

3. 子进程执行到 `__AFL_LOOP` 处，第一次执行循环，所以清空 `__afl_area_ptr` ，设置 `__afl_prev_loc` 的值为0，并向 `__afl_area_ptr` 指向的共享内存的第一个元素写入一个1，然后设置循环次数为1000，修改 `first_pass` 变量值为0，返回1，满足while的条件，开始执行 `fuzzFunc()`；

4. 第一次 `fuzzFunc()` 执行结束，再来到 `__AFL_LOOP`，此时循环次数 - 1 = 999，并抛出 `SIGSTOP` 信号暂停当前进程。因为在 `__afl_start_forkserver` 中设置了 `WUNTRACED` ，所以 waitpid 函数返回，fork server 进程继续执行；

5. fork server 进程接收到 `SIGSTOP` 信号，确认子进程执行结束，表示 `fuzzFunc` 执行结束，所以通过 `WIFSTOPPED` 设置 `child_stopped=1`，并向状态管道写入4字节，通知 afl ，表示本次 fuzz 执行结束；

6. 再次接收到 afl 的 fuzz 通知，此时 `child_stopped=1`， 所以不会再进行 fork ，而是通过 kill 的方式来恢复子进程，并设置 `child_stopped=0`；

7. 此时相当于重新执行程序，所以将 `__afl_prev_loc` 设置为0，并向共享内存的第一个元素写入1，然后直接返回1，此时`while(__AFL_LOOP)`满足条件，于是执行一次 `fuzzFunc`，然后因为是 while 循环，会再次进入`__AFL_LOOP`里，再次减少一次循环次数变成998，并发出信号暂停；

8. 上述过程重复执行，第1000次执行时，先恢复执行，然后返回1，然后执行一次 `fuzzFunc`，然后因为是while循环，会再次进 `__AFL_LOOP` 里，再次减少一次循环次数变成0，此时循环次数 `cnt` 已经被减到0，就不会再发出信号暂停子进程，而是设置`__afl_area_ptr`指向一个无关数组`__afl_area_initial`，随后将子进程执行到结束。

   

重新整理一下上面的逻辑

   - loop 第一次执行，进行初始化，然后返回1，执行一次 `fuzzFunc`，然后 `cnt` 减到999，抛出信号暂停子进程。
   - loop 第二次执行，恢复执行，清空一些值，然后返回1，执行一次 `fuzzFunc`，然后 `cnt` 减到998，抛出信号暂停子进程。
   - loop 第 1000 次执行，恢复执行，清空一些值，然后返回1，执行一次 `fuzzFunc`，然后 `cnt` 减到0，设置指向无关数组，返回0，while循环结束，程序也将执行结束。

- 此时 fork server 不再收到 `SIGSTOP` 信号，于是 `child_stopped`为0。

- afl 通知 fork server再进行一次fuzz的时候，由于此时 `child_stopped` 为0，则 fork server 会先 fork 出一个子进程，然后后续过程和之前一样。

### 3. 'trace-pc-guard' mode

该模式需要先构建 `afl-clang-fast` 时指定 `AFL_TRACE_PC=1`，在使用 `afl-clang-fast` 时加上 `fsanitize-coverage=trace-pc-guard` 参数来开启该功能。这种模式下的插桩，会在每个 edge 处都进行插桩，而不再是基本块。

函数 `__sanitizer_cov_trace_pc_guard` 会在每个 edge 处进行调用：

```c
void __sanitizer_cov_trace_pc_guard(uint32_t* guard) {
  __afl_area_ptr[*guard]++;
}
```

利用函数参数 `guard` 指针所指向的 `uint32` 的值来确定共享内存上所对应的地址。该指针的初始化位于 `__sanitizer_cov_trace_pc_guard_init` 函数中：

```c
void __sanitizer_cov_trace_pc_guard_init(uint32_t* start, uint32_t* stop) {

  u32 inst_ratio = 100;    // 插桩密度设置为100
  u8* x;

  if (start == stop || *start) return;

  x = getenv("AFL_INST_RATIO");   // 获取插桩密度环境变量
  if (x) inst_ratio = atoi(x);

  if (!inst_ratio || inst_ratio > 100) {		// 校验密度值
    fprintf(stderr, "[-] ERROR: Invalid AFL_INST_RATIO (must be 1-100).\n");
    abort();
  }

  /* Make sure that the first element in the range is always set - we use that
     to avoid duplicate calls (which can happen as an artifact of the underlying
     implementation in LLVM). */

  *(start++) = R(MAP_SIZE - 1) + 1;  // 使用随机数进行定位

  while (start < stop) {

    if (R(100) < inst_ratio) *start = R(MAP_SIZE - 1) + 1;
    else *start = 0;

    start++;
  }
}
```

LLVM 设置 `guard` 的首尾分别为 `start` 和 `stop` ，从第一个 `guard` 开始向后进行遍历，并通过`R(MAP_SIZE)`设置其指向的值。

# 参考链接

1. [https://eternalsakura13.com/2020/08/23/afl/#more](https://eternalsakura13.com/2020/08/23/afl/#more)
