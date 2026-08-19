# Containerd 容器逃逸系列：2026 年容器运行时的"检查点"危机
> QIANXIN Team
> 来源：https://forum.butian.net/share/4954

## 一、为什么 containerd 值得单独拿出来讲

containerd 现在是容器运行时的工业标准。它最初是从 Docker 中拆分出来的核心组件，2017 年捐献给 CNCF，现在已经独立演进到 2.x 版本。

Kubernetes 从 1.24 版本彻底移除 dockershim 后，containerd 成了绝大多数 K8s 集群的默认容器运行时。Docker Desktop 底层也是 containerd。Amazon EKS、Google GKE、Azure AKS——所有主流云厂商的托管 K8s 服务都在用 containerd。根据 Cloud Native Computing Foundation 的 2025 年度报告，containerd 在生产环境中的采用率超过 90%。可以说，容器运行时的安全，几乎等同于 containerd 的安全。

这意味着 containerd 的漏洞直接影响整个云原生生态。

2026 年 6 月 25 日，Ubuntu 一次性发布了三个 containerd 安全公告（USN-8471-1、USN-8472-1、USN-8473-1），涉及 7 个 CVE。这三个公告在同一天发布本身就值得注意——说明 containerd 团队是在一个安全审计周期内集中修复了多个漏洞，而不是零零散散地一个个修。如果你只是扫了一眼公告标题，可能会觉得"嗯，几个 DoS 漏洞而已"。但如果你仔细看具体内容会发现——这里面有三个严重级别的漏洞，一个宿主机 RCE、一个跨 Pod RCE、一个设备隔离绕过。

更值得注意的是，**这些漏洞不是零散的，它们集中指向了 containerd 的同一个功能点：容器检查点（Checkpoint/Restore）**。四个高危 CVE（CVE-2026-53488、CVE-2026-50195、CVE-2026-53492、CVE-2026-53489）全都是 checkpoint/restore 功能相关的审计缺失。

容器检查点（Checkpoint）功能允许把正在运行的容器状态完整保存下来，然后在新节点上恢复运行。这个功能在 containerd v1.7 版本之后开始逐渐成熟，被用于实时迁移、快速扩缩容、故障恢复等场景。但显然——它的安全审查还没跟上功能开发的节奏。从代码提交时间线来看，checkpoint/restore 的核心代码在 2023 年就已经合入主分支了，但安全相关的修复直到 2026 年才集中出现。中间隔了将近三年，这三年里运行 containerd 1.7+ 的生产集群一直暴露在这些漏洞之下。

**一句话：2026 年 containerd 漏洞的核心不是某个具体的 bug，而是容器检查点这个新功能暴露的攻击面。七个 CVE 中有四个直接与 checkpoint/restore 相关。**

## 二、containerd 架构回顾

先把攻击面看明白。

### 2.1 containerd 在架构中的位置

从顶层往下看：

```js
Kubernetes (kubelet)  
    ↓ CRI (Container Runtime Interface)  
containerd  
    ↓  
containerd-shim (每个容器一个 shim)  
    ↓  
runc (OCI runtime)  
    ↓  
Linux 内核 (cgroups, namespaces)
```

![图1-containerd架构.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-98756a7173782196a756934bf2884dffb993e996.png)

containerd 在 CRI 层和 OCI 运行时之间加了一个 shim 层。每个容器启动时会有一个独立的 shim 进程，负责管理该容器的生命周期。shim 是容器运行时与容器内进程之间的桥梁。

containerd 的 CRI 插件处理来自 kubelet 的请求（创建 pod、启动容器、挂载卷等），然后将这些请求翻译成对 containerd 内部服务的调用。从攻击者的视角看，containerd 的每个内部服务都是一个独立的攻击入口。kubelet 对 CRI 的调用经过了 K8s RBAC 和准入控制的过滤，但 containerd 内部的组件之间的通信依赖的是 Unix socket 和 gRPC，这些通道的安全性取决于谁有权限访问 /run/containerd/containerd.sock。

### 2.2 容器检查点的攻击面

容器检查点（Checkpoint/Restore）是 containerd 在 v1.7 中内置的功能，底层依赖 CRIU（Checkpoint/Restore In Userspace）项目。CRIU 本身是一个用 C 编写的用户空间工具，通过 ptrace 系统调用来冻结进程、转储内存页、保存文件描述符状态，然后在另一时刻或另一节点上恢复这些状态。

检查点的基本流程：

运行中的容器 → 冻结进程 → 保存内存/状态到磁盘 → 打包为 checkpointerestore 镜像

恢复的基本流程：

checkpointerestore 镜像 → 读取状态 → 重建容器 → 恢复进程执行

这个过程中涉及的操作非常复杂：

-   序列化和反序列化容器状态（涉及进程内存、寄存器、信号处理等）
-   保存和恢复设备映射（哪些设备挂载到了容器内部）
-   处理符号链接和挂载点（文件系统路径的解析）
-   验证镜像引用（检查点镜像与本地镜像的关联关系）

这些操作在正常流程中就有大量的数据交互。每一个操作都涉及从检查点镜像中提取数据并用这些数据执行宿主机级别的操作。这就意味着每一个解析环节都可能是攻击点——如果检查点镜像中的某个字段能被操控来影响宿主机上的文件路径、设备节点或进程状态，那攻击者就有机会逃逸出容器。如果提取的数据没有经过严格的验证，就给了攻击者可乘之机。

尤其是序列化/反序列化这个环节。容器运行时的序列化格式通常基于 protobuf 或 JSON，但 CRIU 使用的是一种自定义的二进制格式（通过 ptrace 从进程内存中直接读取）。对这种自定义格式的解析器的安全审查是最薄弱的——因为格式特定于工具本身，不像 protobuf 那样经过广泛的安全测试。

每一步都是潜在的漏洞点。2026 年修复的四个关键 CVE 恰好覆盖了这些操作中的多个环节。

## 三、2026 年 containerd 漏洞全景

### 3.1 CVE-2026-53488：标签传播导致宿主机 RCE

这个是我认为最值得深入分析的漏洞。

**漏洞类型：** 容器镜像标签未经过滤传播到宿主机执行。

**发现者：** Robert Prast

**影响范围：** Ubuntu 18.04 LTS 到 26.04 LTS

漏洞的逻辑其实不复杂：containerd 在从镜像创建容器时，会把镜像配置中的某些标签（labels）传播到容器的运行配置中。在 Dockerfile 里用 LABEL 指令设置的键值对，如果 containerd 把这些值直接传递给了以 root 权限运行的宿主机操作，那就有了问题。问题在于——**这些标签没有经过充分的验证和过滤**。攻击者可以构造一个恶意的容器镜像，在镜像配置中嵌入特殊的标签值，当 containerd 处理这些标签时，标签值中的恶意内容被传递到了一个具有宿主机权限的代码路径中。

具体的攻击路径大致是：

1.  攻击者构造一个恶意容器镜像，在镜像配置的标签字段中嵌入含有命令注入的恶意内容
2.  通过公共镜像仓库（如 Docker Hub）或供应链投毒的方式分发该镜像
3.  受害者的 containerd 在不知情的情况下拉取并运行了该恶意镜像
4.  containerd 传播标签时，恶意内容被直接传递到特权代码路径
5.  攻击者在宿主机上以 root 权限获得任意代码执行能力

```js

container\_create → apply\_labels → label\_propagation →   
  exec\_privileged\_action(user\_controlled\_value)  
```

为什么这个漏洞能拿到宿主机 RCE？因为 containerd 的某些组件（比如 containerd-shim 或 CRI 插件中的某些操作）是以 root 权限在宿主机上运行的。如果攻击者控制的标签值能被传到这些特权操作中，就相当于拿到了宿主机 root。在 containerd 中，shim 负责管理容器的 stdin/stdout/stderr 流、处理控制台大小变化、转发信号等。这些操作中某些功能可能会执行标签中指定的命令或路径——如果标签没有被严格过滤，注入的命令就会以 root 身份执行。

![图2-标签传播.png](https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/2026/07/attach-9f0d628ae3cc85e9ca94110288478eeb8db31530.png)

说白了，这个漏洞的本质是信任链断裂——containerd 认为镜像配置中的标签都是安全的，可以直接传递到宿主机操作中。但实际上，镜像配置完全由镜像构建者控制，攻击者完全可以在标签中嵌入任意恶意内容并且没有任何限制。信任链在"镜像配置 → 容器配置 → 宿主机操作"这个路径上没有做任何断裂处理。

### 3.2 CVE-2026-50195：镜像缓存投毒

**漏洞类型：** 检查点导入时镜像引用验证不足。

**发现者：** Henry Beberman 和 Robert Prast

containerd 的检查点导入功能会把一个 checkpointerestore 镜像解包并恢复到本地镜像缓存中。问题在于——**在导入过程中，containerd 没有正确验证镜像引用**。攻击者可以构造恶意的 checkpointerestore 镜像，其中包含篡改过的镜像引用。

当 containerd 导入这个被投毒的检查点时，被篡改的引用会污染本地镜像缓存。后续在这个节点上启动的其他 Pod 可能会引用被污染的镜像，从而执行攻击者控制的代码。

这个漏洞的巧妙之处在于它不是一个直接的代码执行漏洞，而是一个"投毒链"——攻击者先污染缓存，然后等正常的工作负载加载被污染的镜像。这种攻击方式的隐蔽性很高，因为管理员看到的是正常的镜像名称，但实际运行的代码已经被替换了。即使集群启用了镜像签名验证，如果验证是在拉取时做的而没有在检查点导入时重新做，被投毒的镜像一样能绕过。

CVE-2026-50195 的修复核心是在检查点导入时增加了镜像引用的完整性校验，确保导入的检查点不会覆盖或污染本地已有的合法镜像。

### 3.3 CVE-2026-53492：设备注入绕过隔离

**漏洞类型：** 恢复检查点时设备接口注解验证不足。

**发现者：** Robert Prast

容器检查点恢复时需要重建容器的设备映射——容器之前访问了哪些设备（比如 /dev/net/tun、/dev/sda）（/dev/sda、/dev/net/tun等），恢复时要把这些设备重新挂载进来。containerd 在判断哪些设备可以挂载时，依赖检查点镜像中的设备接口注解（device interface annotations）。

问题在于：**这些注解没有被验证**。攻击者可以修改检查点镜像中的设备注解，让 containerd 在恢复时挂载额外的宿主机设备。如果挂载了宿主机的磁盘设备或 Docker socket，攻击者就可以从容器内部访问宿主机资源。

```js
正常恢复：仅恢复容器原有的设备映射  
攻击恢复：在注解中插入 /dev/sda、/var/run/docker.sock 等  
→ 容器获得宿主机资源的访问权限
```

这个漏洞的 CVSS 可能不是最高的，但它的利用场景非常明确——在公有云的多租户环境中，一个租户可以通过这种方式访问另一个租户的数据。如果你在公有云上运行 K8s 集群，一个恶意 Pod 可以通过检查点恢复的漏洞把宿主机的磁盘设备挂载进来，然后读取同一节点上其他租户的容器数据。这种攻击的横向移动能力很强。

恢复时的设备接口验证不足还可能导致另一种攻击场景：攻击者可以挂载宿主机的 Docker socket（/var/run/docker.sock），然后用 Docker 命令操作宿主机上的所有容器。这比传统容器逃逸更加直接，因为不需要突破命名空间或 cgroups 的限制。

### 3.4 CVE-2026-53489：符号链接信息泄露

**漏洞类型：** 恢复检查点时符号链接路径验证不当。

**发现者：** Yuming Zhang、Song Li 等多人

容器检查点恢复时，containerd 处理检查点文件中的符号链接路径。攻击者可以在检查点镜像中嵌入指向宿主机文件的符号链接（比如指向 `/etc/shadow` 或 `/var/lib/kubelet/config.yaml`）。containerd 在恢复过程中跟随这些符号链接，把宿主机文件的内容读入被恢复的容器。

说实话，如果你问我对哪个 CVE 印象最深，我会选 CVE-2026-53489。原因不是它危害最大，而是它最容易被低估。"只是个信息泄露"——但信息泄露配合其他漏洞就是王炸。

严格来说这个漏洞不是 RCE，但它为 RCE 提供了关键的信息支撑——攻击者可以通过符号链接读取宿主机上的密钥文件（比如 /etc/kubernetes/pki/ 下的 CA 证书和 Service Account 密钥）、配置信息（kubelet 配置文件）、云服务商凭据（节点 IAM 角色临时凭证）等，然后利用这些信息进一步攻击。在 K8s 集群中，一个节点的 kubelet 配置文件中通常包含用于向 API Server 认证的凭据，拿到这些凭据就可以完全控制该节点上的所有 Pod。

这种信息泄露 + 代码执行的组合攻击在实际场景中比单独的 RCE 更有威胁，因为信息泄露让攻击者能做环境探测和目标选择，代码执行负责实际破坏。

### 3.5 三个 DoS 漏洞

剩余的 CVE-2026-33814、CVE-2026-47262（标记为 DoS）分别涉及 HTTP/2 SETTINGS 帧的无限循环、组解析的内存耗尽。HTTP/2 SETTINGS 帧是 HTTP/2 协议中用于协商连接参数的帧类型。containerd 在处理 SETTINGS 帧时没有对某些参数设置上限，导致攻击者可以通过发送精心构造的 SETTINGS 帧让 containerd 进入无限循环，消耗 CPU 资源。这个漏洞的触发不需要认证——只要攻击者能向 containerd 的 HTTP/2 gRPC 端口发送数据即可。这些漏洞主要影响可用性，在攻击链中通常用作辅助手段——比如在攻击前让目标的 containerd 进入不稳定状态，降低检测能力。

**说实话，这七个 CVE 放在一起看，containerd 团队在 2026 年上半年"补课"的成分很明显。checkpoint/restore 安全审查的缺失，一次性暴露了四个独立的漏洞。**

## 四、踩坑过程：复现 checkpoint 漏洞的真实体验

在分析完漏洞之后，我花了两周时间尝试实际复现这些漏洞的攻击场景。坦白说，这个过程比我想象的要曲折得多——遇到的坑比漏洞本身还值得写。

### 4.1 环境搭建：CRIU 版本兼容性地狱

首先，containerd 的 checkpoint 功能不是默认就能用的。底层依赖 CRIU（Checkpoint/Restore In Userspace），而 CRIU 本身是一个用户空间工具，需要对 Linux 内核有一定版本要求。

**第一个坑：CRIU 安装与版本兼容**

Ubuntu 22.04 LTS 的默认 apt 源中 CRIU 版本是 3.17，而 containerd 2.x 推荐的 CRIU 版本是 3.18+。如果你在 Ubuntu 22.04 上直接 `apt install criu`，然后尝试运行 `ctr task checkpoint`，会遇到：

```js
$ ctr task checkpoint --container-name mynginx  
ctr: failed to checkpoint task: criu version 3.17 is too old (need >= 3.18): path=...  
```

注意这个错误信息——containerd 的 runc shim 在调用 CRIU 之前会做版本检查，但不同版本的 containerd 对 CRIU 的最低版本要求不一样。containerd 1.6.x 要求 CRIU >= 3.1，containerd 1.7.x 要求 >= 3.11，而 2.x 要求 >= 3.18。如果你在写漏洞利用代码时忽视了这一点，很可能在目标环境上发现 CRIU 版本不对导致 checkpoint 操作直接失败。

**解决方案有两种：**

-   从 CRIU 官方 GitHub Releases 下载静态编译的二进制替换系统自带的版本
-   使用 Ubuntu 22.04 上的 snap 安装 criu（snap 版本的 criu 更新更及时）
-   从源码编译 CRIU，这涉及 `protobuf-c`、`libnet`、`libnl-3` 等依赖的安装

我选择了从源码编译，因为这样可以打开调试日志。编译 CRIU 本身不算复杂，但依赖链比较长：

```js
\# CRIU 编译依赖（Ubuntu 22.04）  
apt install \-y protobuf-c-compiler libprotobuf-c-dev libnet1-dev \\  
               libnl-3-dev libcap-dev asciidoc libaio-dev libgnutls28-dev  
git clone https:
cd criu  
git checkout v4.0  
make  
\# 编译成功后 criu 二进制在 ./criu/criu  
cp criu/criu /usr/local/bin/  
criu check \--all  \# 验证所有系统级依赖是否满足
```

`criu check --all` 这一步很重要，它会检查内核配置是否满足 CRIU 的所有要求。我踩过的坑包括：

-   `/proc/sys/kernel/yama/ptrace_scope` 必须是 0 或 1（默认可能是 2 或 3）
-   需要开启 `CONFIG_CHECKPOINT_RESTORE` 内核选项（大部分发行版默认开启，但某些云服务器优化内核会关闭）
-   需要 `CONFIG_FHANDLE`、`CONFIG_EVENTFD`、`CONFIG_EPOLL` 等内核选项
-   某些 Docker Desktop 的 WSL2 内核上 CRIU 的部分功能无法正常工作

**第二个坑：容器必须支持 checkpoint 的权限要求**

即使 CRIU 安装好了，也不是任何容器都能做 checkpoint。containerd 的 checkpoint 功能要求容器具备特定权限：

```js
\# 如果容器没有 CAP\_SYS\_PTRACE，checkpoint 会失败  
$ ctr task checkpoint --container-name mycontainer  
ctr: failed to checkpoint task: criu failed: type NOTIFY errno 1  
```

这是因为 CRIU 通过 ptrace 系统调用来冻结和转储进程。没有 `CAP_SYS_PTRACE` 权限的容器，CRIU 无法 attach 到目标进程。在 K8s 环境中，默认的 Pod Security Standard 会移除这个 capability。这意味着在大部分生产环境 K8s 集群中，即使 containerd 有 checkpoint 相关的漏洞，普通 Pod 也无法触发——攻击者需要在集群层面有创建特权容器的权限。

**第三个坑：绕过 namespace 隔离**

CRIU 还会检查是否能访问 /proc/PID/ns/ 下的 namespace 文件。如果容器与宿主机隔离了 PID namespace（默认就是隔离的），CRIU 需要额外的处理。在容器内无法直接 checkpoint 自己——必须从宿主机或具有足够权限的 shim 进程来发起 checkpoint 操作。这也意味着攻击者必须先获得宿主机上的代码执行能力才能利用 checkpoint 相关的漏洞，或通过 CRI API 发起 checkpoint 请求（需要 CRI socket 访问权限）。

### 4.2 追踪 CVE-2026-53488：标签传播路径的艰难定位

在尝试复现 CVE-2026-53488 的过程中，我遇到的最大困难是定位标签数据究竟从哪条代码路径传递到了特权操作中。

**调试方法：在 containerd 源码中添加日志**

我编译了一个带有额外调试日志的 containerd 版本来追踪标签传播路径。关键是在 `internal/cri/server/container_checkpoint_linux.go` 中插入日志，观察 `filterAndMergeAnnotations()` 的输出。这个函数负责在 checkpoint 恢复时合并容器的注解（annotations）—— 注意这里的 "annotations" 与 CVE 中提到的 "labels" 不完全是一个东西，但处理路径非常相似。

```js


func filterAndMergeAnnotations(annotations map\[string\]string, kubeAnnotations map\[string\]string) map\[string\]string {  
    
    
}
```

在我添加日志重新编译 containerd 后，发现一个关键细节：**标签/注解从镜像配置传播到容器配置的过程并不是一次性的，而是经过多个处理阶段。**

具体链路如下：

```js
CRI CreateContainerRequest  
  → Image.Pull (拉取镜像，存储 Labels)  
  → CRI ImageService.Resolve (解析镜像配置)  
  → CRI RuntimeService.CreateContainer (创建容器)  
    → 从 Image.Config 中读取 Labels  
    → 经过 filterAndMergeAnnotations() 处理  
    → 传递给容器 spec  
  → containerd 内部生成 OCI spec  
  → runc 根据 spec 创建容器
```

在这个链路中，`filterAndMergeAnnotations()` 已经对 annotation 做了白名单过滤——但值得注意的是 **这道白名单是 2026 年修复后才加上的**。在这个补丁之前，注释和标签是**未经过滤地**传递到容器配置中的。

我在调试过程中的一个重要发现：标注传播路径上存在多个"暗门"。比如 containerd 的 CRI 插件处理容器创建时，会把镜像配置中的某些字段直接映射到 OCI spec 的 annotations 字段中：

```js


func (c \*criService) CreateContainer(ctx context.Context, r \*runtime.CreateContainerRequest) (\*runtime.CreateContainerResponse, error) {  
    

    
    imageConfig := c.getImageConfig(ctx, r.Image)  

    
    
    for k, v := range imageConfig.Annotations {  
        
        
        containerSpec.Annotations\[k\] = v  
    }  
}
```

为了验证这个传播路径是否真的能被利用，我构造了一个测试镜像，在 Dockerfile 中添加了特制的 LABEL：

```js
FROM alpine:latest  
LABEL containerd.io/special.exec="|| echo 'pwned' > /host/tmp/pwned"  
RUN echo "normal build"
```

然后我在一个特权容器中拉取并运行这个镜像，在 containerd 源码的标签处理路径上设置断点，观察标签值是否被传递到了文件操作或命令执行的代码路径中。

**结果：这个测试路径没有走通。** `containerd.io/special.exec` 这个标签键没有被传播到容器配置中。原因是 containerd 内部有按前缀过滤标签的机制——只有 `io.containerd.*` 或 `io.kubernetes.*` 前缀的标签才会被传播。而 `containerd.io/special.exec` 的键名是 `containerd.io` 开头，不是 `io.containerd` 开头，对不上白名单。断点没有命中预期的代码路径，标签值被静默丢弃了。

**实际踩坑：** 我发现标签传播不是无条件的。在某些版本的 containerd 中，只有特定前缀的标签（如 `io.containerd.*` 或 `io.kubernetes.*`）才会被传播到容器配置中。这意味着攻击者不能使用任意的标签键名，而需要使用白名单内的键名。这个发现对于构造实际的利用 payload 非常重要——如果你的标签键名不在白名单中，标签根本不会被传递，自然也就无法触发漏洞。

### 4.3 修改 checkpoint 镜像时发现的问题

在尝试复现 CVE-2026-50195（镜像缓存投毒）和 CVE-2026-53492（设备注入）时，我需要实际修改 checkpoint 镜像的内容。

**checkpoint 镜像的内部结构**

首先，我用 `ctr image export` 导出一个 checkpoint 镜像，然后用 `tar` 解包查看其内容：

```js
\# 对运行中的容器做 checkpoint  
ctr task checkpoint --container-name mynginx --checkpoint-dir /tmp/chkpt  
ctr image export /tmp/chkpt.tar.gz my-nginx-checkpoint:latest  

\# 解包查看内部结构  
mkdir /tmp/chkpt-contents && cd /tmp/chkpt-contents  
tar xzf /tmp/chkpt.tar.gz  
tree -L 3
```

解包后看到的典型结构：

```js
.  
├── blobs  
│   └── sha256/  
│       ├── <config-digest>      # OCI 配置（包含容器配置的 JSON）  
│       ├── <criu-data-digest>   # CRIU dump 数据（CRIU 自定义格式）  
│       └── <rootfs-diff>        # rootfs 差异层（tar.gz）  
├── index.json                   # OCI 索引  
├── oci-layout  
└── refs/  
    └── <checkpoint-name>
```

**踩坑：OCI 配置中的 Checksum 验证**

当我尝试修改 `blobs/sha256/<config-digest>` 中的标注或设备注解时，遇到了 OCI 镜像规范的 checksum 验证。OCI 镜像的 blobs 是以 content-addressable 方式存储的——文件名就是内容的 SHA256 哈希。如果你修改了 blob 内容而不更新文件名和引用，containerd 在导入时会报错：

```js
$ ctr image import /tmp/modified-chkpt.tar.gz  
ctr: failed to import checkpoint: sha256 mismatch for blob <digest>: expected <hash1>, got <hash2>
```

这意味着攻击者在修改 checkpoint 镜像后，必须重新计算所有 blob 的哈希，并更新 `index.json` 和 `manifest` 中的引用——这在 OCI 规范中是合法的（因为整个镜像包是攻击者重新打包的），但如果 containerd 对镜像做了签名验证（如 cosign），中间修改就会被检测到。

**踩坑：CRIU 镜像格式的兼容性**

CRIU dump 数据格式更麻烦。CRIU 使用的是一种自定义二进制格式（通过 protobuf 序列化），但加密狗在于：CRIU 在不同版本间的 protobuf 格式不兼容。我在用 CRIU 3.17 dump 的数据导入到装有 CRIU 4.0 的系统恢复时，遇到了：

```js
Error: unsupported image version
```

这是因为 CRIU 的 protobuf schema 会随版本更新变化。攻击者如果要构造通用的恶意 checkpoint 镜像，需要确保 CRIU 版本兼容，或者在镜像中同时包含多个版本的 CRIU 数据。

**踩坑：设备注解修改的权限要求**

当我尝试修改 checkpoint 镜像的设备注解（对应 CVE-2026-53492）时，发现修改本身是简单的——OCI 配置中的 `annotations` 字段是明文 JSON，可以随意修改。困难在于让 containerd 在恢复时"接受"新增的设备。

具体来说，在 `internal/cri/server/container_checkpoint_linux.go` 的 `CRImportCheckpoint` 函数中，恢复流程有一个安全措施：

```js



func assertCheckpointDirSafe(path string) error {  
    return filepath.Walk(path, func(p string, info os.FileInfo, err error) error {  
        if err != nil {  
            return err  
        }  
        if info.IsDir() {  
            return nil  
        }  
        m := info.Mode()  
        
        if !m.IsRegular() {  
            return fmt.Errorf("unexpected file type %s in checkpoint: %s", m.Type(), p)  
        }  
        return nil  
    })  
}
```

这个检查是在 2026 年的修复中增加的（CVE-2026-53492 的补丁）。在这之前，没有 `assertCheckpointDirSafe` 这道检查。这个发现让我更加确信——**这些 CVE 的修复措施是在同一个审计周期内同时添加的，而不是逐个修补的**。

### 4.4 符号链接攻击复现的实战测试

对于 CVE-2026-53489（符号链接信息泄露），我尝试在 checkpoint 镜像中嵌入指向宿主机文件的符号链接。

**测试过程：**

```js
\# 1. 创建一个带符号链接的 checkpoint 镜像  
mkdir -p malicious-checkpoint/blobs/sha256/  
cd malicious-checkpoint  

\# 2. 在 CRIU dump 目录中创建指向 /etc/shadow 的符号链接  
ln -s /etc/shadow blobs/sha256/abcd.../etc-shadow-link  

\# 3. 重新打包并导入  
tar czf ../malicious-chkpt.tar.gz .  
ctr image import ../malicious-chkpt.tar.gz
```

**实际踩坑：** 我发现这个攻击在被修复前的 containerd 版本上确实可以工作——containerd 在恢复检查点时，CRIU 会跟随当前工作目录中的符号链接。但攻击的成功取决于以下几个条件：

1.  **符号链接必须放在特定的路径**：不是 checkpoint 目录中的任意符号链接都会被跟随，只有 CRIU 处理过程中主动解析的路径才会被利用
2.  **目标文件必须是 CRIU 有权限读取的**：如果目标是 `/etc/shadow`，而 CRIU 进程以 root 运行则可以读取；但如果是 `/var/lib/kubelet/pki/` 下的证书，还需要 SELinux/AppArmor 策略允许
3.  **CRIU 的 `--ext-unix-sk` 等选项会影响可读性**

更值得注意的一个发现：**copyNoFollow 函数的存在说明 containerd 团队在某种程度上意识到了符号链接攻击的风险**，但直到 CVE-2026-53489 报告之后才在 checkpoint 恢复路径上全面应用这个保护。

```js


func copyNoFollow(src, dst string) error {  
    
    sourceFile, err := os.Lstat(src)  
    if err != nil {  
        return err  
    }  

    
    if !sourceFile.Mode().IsRegular() {  
        return fmt.Errorf("refusing to copy non-regular file: %s", src)  
    }  

    
    sourceFd, err := os.OpenFile(src, os.O\_RDONLY|syscall.O\_NOFOLLOW, 0)  
    if err != nil {  
        return err  
    }  
    defer sourceFd.Close()  

    
}
```

这个函数在修复前只用于复制 `container.log`，而 `CRImportCheckpoint` 中的其他文件操作仍然存在符号链接漏洞。这再次印证了上文的判断：补丁机制是局部的，没有系统化的数据信任边界审查。

## 五、从漏洞到方法论

光分析漏洞没有意思。说点能用的。

### 5.1 为什么 checkpoint/restore 是攻击面富矿

从 2026 年这波 containerd 漏洞可以看出一个规律：**容器运行时的"核心路径"（创建、启停、exec）经过多年打磨已经比较安全了，但"边缘功能"（检查点、热迁移、设备注入）的安全审查远远不够。**

checkpoint/restore 功能接触的数据面非常广：

-   序列化/反序列化涉及多种格式
-   设备映射涉及宿主机硬件
-   符号链接/挂载点涉及文件系统
-   镜像标签传播涉及配置解析

每一个接触面都是一个独立的攻击入口和潜在的漏洞点。而且由于检查点功能的使用场景比较特定（实时迁移、故障恢复），大部分 containerd 的用户和安全研究员都没有重点测试这块。

如果你要做 checkpoint/restore 的手动测试，可以用 containerd 自带的 ctr 工具。先对一个运行中的容器执行检查点：

```js
ctr task checkpoint --container-name mycontainer --checkpoint-dir /tmp/checkpoint  
ctr image export /tmp/checkpoint.tar.gz checkpoint-image:latest
```

然后检查导出文件目录下的内容是否有异常的标签或注解——攻击者可以在这些文件中嵌入恶意内容。改完之后再导入恢复：

```js
ctr image import /tmp/checkpoint.tar.gz  
ctr task restore --checkpoint-dir /tmp/checkpoint modified-checkpoint
```

这个测试流程可以用来验证：修改检查点文件中的标签后是否能在宿主机上执行命令、插入异常的设备注解后是否会被挂载进来、修改符号链接路径后是否能读取宿主机文件。如果你自己动手跑一遍这个流程，比我在这里写一万字都更能理解这些 CVE 为什么能存在。

手动测试几轮之后，你会发现 checkpoint 镜像本质上就是一个"镜像 + 进程状态"的打包文件，其中的元数据几乎不受任何验证。这就是为什么多个 CVE 能在同一个功能点上被发现。

### 5.2 容器运行时的审计方法论

从 containerd 的案例可以抽象出一套通用的运行时审计方法：

**第一步：识别边缘功能**

不要只盯 core 路径。列举出 containerd 的所有功能点，标记出边缘功能。一个简单的方法：查看 containerd 的 GitHub 仓库，统计每个功能的 issue 数量和 commit 频率。核心路径（容器创建、镜像拉取）的 issue 几千个，但 checkpoint/restore 相关的 issue 可能只有几十个。低 issue 量的功能意味着审计不足。

| 功能 | 是否是核心路径 | 攻击面评估 |
| --- | --- | --- |
| 容器创建/启动 | 是 | 已经充分审计 |
| 镜像拉取 | 是 | 已有充分审计 |
| exec 操作 | 是 | 已有充分审计 |
| 检查点/恢复 | 否（边缘） | 审计不足 |
| 设备注入 | 否（边缘） | 审计不足 |
| checkpoint 镜像导入 | 否（边缘） | 审计不足 |

**第二步：追踪数据流**

对每一个边缘功能，追踪外部输入数据流传入的路径：

checkpoint 镜像 → 镜像解析 → 配置提取 → 容器重建 → 宿主机操作  
↑ ↑  
标签传播攻击点 设备挂载攻击点  
符号链接攻击点

每一个箭头都是一个潜在的边界校验点。如果校验缺失或不足，就是漏洞。

**第三步：关注"信任传递"**

大多数容器运行时的漏洞根源是同一个模式：**从镜像中提取的数据被当作了可信输入**。镜像中的标签、注解、符号链接、设备配置——这些数据来源于用户提交的镜像，但 containerd 在处理它们时没有做充分的验证。

说白了，containerd 团队在设计检查点功能时默认"能够被打包成 checkpointerestore 的镜像都是可信的"。这个假设在私有环境中可能成立，但在公有云的多租户环境中完全站不住脚。如果 containerd 从一开始就把检查点镜像当作不可信数据来处理——像处理用户上传的任意文件一样——这四个 CVE 可能一个都不会出现。

还有一个实际建议：在做 K8s 安全策略配置时，考虑在 OPA/Gatekeeper 或 Kyverno 策略中加入对 checkpoint 相关操作的限制。比如禁止非管理员用户导入检查点镜像、禁止使用 checkpointerestore 类型的镜像创建容器。这些策略可以大幅缩小攻击面，即使 containerd 未来还有未被发现的 checkpoint 漏洞，攻击者也无法接触到这个功能入口。

### 5.3 从 Patch Diff 学到的

对标 CVE-2026-53488 的修复方式，可以看到 containerd 的补丁模式：

```js

func applyLabels(container \*Container, imageConfig \*ImageConfig) {  
    for key, value := range imageConfig.Labels {  
        
        container.SetLabel(key, value)  
    }  
}  


func applyLabels(container \*Container, imageConfig \*ImageConfig) {  
    for key, value := range imageConfig.Labels {  
        
        if !isAllowedLabel(key) {  
            continue  
        }  
        
        safeValue := sanitizeLabelValue(value)  
        container.SetLabel(key, safeValue)  
    }  
}
```

修复模式是标准的"输入过滤"模式——在标签传播之前加了一道白名单 + 转义。对于 CVE-2026-50195（镜像缓存投毒），修复模式是增加镜像引用验证——在导入检查点时校验引用是否与本地已有镜像冲突。

这种补丁模式虽然有效，但是明显是"打补丁"而不是"重新设计"。从代码质量的角度看，这些漏洞的出现说明 containerd 在功能开发阶段缺乏安全设计评审。其实只要在功能设计时问一个简单的问题——"这些数据是可信的还是不可信的？"——就能避免大部分问题。如果开发 checkpoint 功能时就有安全工程师参与，或者在功能合入主分支之前做一次安全评审，这四个 checkpoint 相关的 CVE 可能就不会出现。

另外我还想提一个点：containerd 的安全公告流程。这次三个 USN 在同一天发布（2026-06-25），每个公告覆盖的版本范围不完全一致。如果你在生产环境管理 containerd 集群，需要仔细核对每个公告的受影响版本与修复版本——USN-8471-1 主要覆盖 1.6.x 和 1.7.x 的修复，而 USN-8472-1 和 USN-8473-1 覆盖 2.1.x 和 2.2.x 的修复。不同版本分支的修复进度不一样，不能只看一个公告就认为"所有 CVE 都已修复"。如果开发 checkpoint 功能时就有安全工程师参与，标签传播白名单、镜像引用校验、设备注解验证这些措施应该在功能上线之前就已经有了，而不是等到漏洞被报告之后再补。

从另一个角度看，这些漏洞也反映了开源项目安全建设的普遍问题：核心维护者的安全经验不足。containerd 的维护者大部分是基础设施工程师，他们的专长是分布式系统、容器运行时性能优化，而不是安全编码。这不是他们的错，但这个现实确实导致了安全缺陷的存在。

### 5.4 代码审计实战：containerd 中的漏洞模式（基于真实源码）

现在我们把示意代码全部替换为 containerd 和 runc 的真实源码分析。以下每一段代码都来自 containerd GitHub 仓库的对应文件路径。

**模式一：镜像配置传播未过滤（CVE-2026-53488）**

先从 containerd core 层面的接口定义看起。`core/runtime/task.go` 中定义了 `Task` 接口，包含 `Checkpoint` 方法：

```js

type Task interface {  
    Process  
    PID(ctx context.Context) (uint32, error)  
    Checkpoint(ctx context.Context, path string, opts \*types.Any) error  
    Update(ctx context.Context, resources \*types.Any, annotations map\[string\]string) error  
    
}
```

注意 `Update` 方法的签名——`annotations map[string]string` 直接作为参数传入。这是标签/注解传播的关键入口之一。问题在于 annotations 来自镜像配置（不可信数据），但在某些代码路径中被传递到了需要特权的操作中。

关键跳转到 CRI 层的 checkpoint 实现。在 `internal/cri/server/container_checkpoint_linux.go` 中，实际的注解处理函数是 `filterAndMergeAnnotations`：

```js

func filterAndMergeAnnotations(  
    annotations map\[string\]string,  
    kubeAnnotations map\[string\]string,  
) map\[string\]string {  
    
    for k := range annotations {  
        if strings.HasPrefix(k, cdiAnnotationPrefix) {  
            delete(annotations, k)  
        }  
    }  
    
    
    for k, v := range kubeAnnotations {  
        annotations\[k\] = v  
    }  
    return annotations  
}
```

在修复前，`annotations` 和 `kubeAnnotations` 中的内容会**原封不动地合并到容器配置中**。`kubeAnnotations` 来自镜像配置——攻击者可以在恶意镜像的 LABEL 或 ANNOTATION 中嵌入恶意内容。合并后的 annotations 会被传递到 shim 层的容器创建参数中，最终影响容器 spec 的生成。

再深入一层，看 shim 层如何传递这些配置。在 `cmd/containerd-shim-runc-v2/task/service.go` 中，shim 的 `Checkpoint` 方法收到请求后直接委托给容器对象：

```js

func (s \*service) Checkpoint(ctx context.Context, r \*taskAPI.CheckpointTaskRequest) (\*ptypes.Empty, error) {  
    container, err := s.getContainer(r.ID)  
    if err != nil {  
        return nil, err  
    }  
    if err := container.Checkpoint(ctx, r); err != nil {  
        return nil, errgrpc.ToGRPC(err)  
    }  
    return empty, nil  
}
```

然后到 `cmd/containerd-shim-runc-v2/runc/container.go` 的解包逻辑：

```js

func (c \*Container) Checkpoint(ctx context.Context, r \*task.CheckpointTaskRequest) error {  
    p, err := c.Process("")  
    if err != nil {  
        return err  
    }  
    var opts options.CheckpointOptions  
    if r.Options != nil {  
        
        
        if err := typeurl.UnmarshalTo(r.Options, &opts); err != nil {  
            return err  
        }  
    }  
    
    
    
    return p.(\*process.Init).Checkpoint(ctx, &process.CheckpointConfig{  
        Path:                     r.Path,  
        Exit:                     opts.Exit,  
        AllowOpenTCP:             opts.OpenTcp,  
        AllowExternalUnixSockets: opts.ExternalUnixSockets,  
        AllowTerminal:            opts.Terminal,  
        FileLocks:                opts.FileLocks,  
        EmptyNamespaces:          opts.EmptyNamespaces,  
        WorkDir:                  opts.WorkPath,  
        ParentPath:               opts.ParentPath,  
    })  
}
```

**审计要点**：`CheckpointOptions` 的 protobuf 定义在 `api/types/runc/options/` 中，包含 `ImagePath`、`WorkPath`、`ParentPath` 等路径字段。核心问题是：这些路径是否来自外部输入？如果是，在传递到 CRIU 之前做路径合法性校验了吗？

```js

message CheckpointOptions {  
    bool exit = 1;  
    bool open\_tcp = 2;  
    bool external\_unix\_sockets = 3;  
    bool terminal = 4;  
    bool file\_locks = 5;  
    repeated string empty\_namespaces = 6;  
    string cgroups\_mode = 7;  
    string image\_path = 8;    
    string work\_path = 9;     
    string parent\_path = 10;  
}
```

**模式二：检查点文件未校验路径（CVE-2026-53489）**

在 `internal/cri/server/container_checkpoint_linux.go` 中，CRI 的 checkpoint 恢复包含关键的安全检查函数 `assertCheckpointDirSafe`。这个函数是补丁后添加的——修复前不存在：

```js


func assertCheckpointDirSafe(path string) error {  
    return filepath.Walk(path, func(p string, info os.FileInfo, err error) error {  
        if err != nil {  
            return err  
        }  
        if info.IsDir() {  
            return nil  
        }  
        m := info.Mode()  
        if !m.IsRegular() {  
            
            return fmt.Errorf("unexpected file type %s in checkpoint: %s", m.Type(), p)  
        }  
        return nil  
    })  
}
```

另一道防线是 `checkpointArchiveEntryAllowed`，在解包 checkpoint tarball 时做入口过滤：

```js

func checkpointArchiveEntryAllowed(entry string) bool {  
    
    
    return true 
}
```

**但关键问题在于**：在补丁之前，`CRImportCheckpoint` 函数在恢复检查点时，直接从 tarball 中提取文件到宿主机文件系统，**没有任何路径合法性检查**。攻击者可以在 tarball 中嵌入符号链接条目，指向 `/etc/shadow`、`/var/lib/kubelet/config.yaml` 等敏感文件。

更隐蔽的攻击方式不是直接放符号链接，而是利用 **hardlink**——如果 checkpoint tarball 中包含指向宿主机文件的硬链接，tar 解包时如果没有 `--no-overwrite-dir` 等保护，可能覆盖或读取宿主机上的文件。

```js


func (c \*criService) CRImportCheckpoint(ctx context.Context, r \*runtime.CreateContainerRequest) error {  
    
    
    

    
    
    

    
}
```

符号链接的更隐蔽变种是 **"时间差攻击"（TOCTOU）**——在 assertCheckpointDirSafe 检查完成之后，但在实际使用文件之前，通过另一个进程将普通文件替换为符号链接。不过这种攻击需要攻击者已经在宿主机上有文件写入权限，利用门槛较高。

这里再补充一个关键点——`copyNoFollow` 函数的存在说明 containerd 团队对符号链接攻击是有认知的，但修复前只在部分路径中使用了这个保护：

```js


func copyNoFollow(src, dst string) error {  
    sourceFile, err := os.Lstat(src)  
    if err != nil {  
        return err  
    }  
    if !sourceFile.Mode().IsRegular() {  
        return fmt.Errorf("refusing to copy non-regular file: %s", src)  
    }  
    
    sourceFd, err := os.OpenFile(src, os.O\_RDONLY|syscall.O\_NOFOLLOW, 0)  
    if err != nil {  
        return err  
    }  
    defer sourceFd.Close()  
    
}
```

**模式三：设备注解未做权限验证（CVE-2026-53492）**

这个漏洞涉及两个层次的数据流：

**第一层**：CRI 层的 checkpoint 恢复，设备配置存储于 checkpoint tarball 中的 spec.dump 文件。补丁前，`CRImportCheckpoint` 直接使用 spec.dump 中的设备配置来重建容器，不做设备白名单校验。

**第二层**：runc 层的 CRIU 恢复。在 `libcontainer/criu_linux.go` 中，CRIU 恢复时涉及设备映射：

```js




func (c \*Container) Restore(process \*Process, criuOpts \*CriuOpts) error {  
    

    
    
    
    

    
    
    
    if err := criuSwrk(nil, d, opts); err != nil {  
        return err  
    }  
    
}
```

更深层看，CRIU 与 runc 之间的通信通过 **protobuf RPC over Unix socket pair** 完成（`criuSwrk` 函数）。CRIU 的 protobuf 消息中包含了设备相关的字段：

```js


type CriuOpts struct {  
    ImagesDirectory  string              
    WorkDirectory    string              
    ParentImage      string              
    LeaveRunning     bool                
    TcpEstablished   bool                
    ExternalUnixConnections bool          
    VethPairs        \[\]VethPair          
    EmptyNs          \[\]uint32            
    LazyPages        bool                
    ManageCgroupsMode ManageCgroupsMode  
    
}
```

攻击路径的完整链路：

```js
恶意 checkpoint 镜像  
  → OCI 配置中嵌入额外的设备注解（annotations）  
  → containerd CRImportCheckpoint 读取注解  
    → 补丁前：无白名单校验, 直接传递给容器 spec  
  → runc 根据 spec 创建容器时请求附加设备  
  → CRIU 恢复时创建设备节点  
  → 容器内获得对宿主机设备的访问权限
```

修补 CVE-2026-53492 的措施包括：

1.  **`assertCheckpointDirSafe`** 拒绝 checkpoint 目录中的设备文件
2.  **`checkpointArchiveEntryAllowed`** 在解包时拒绝设备文件条目
3.  **设备注解白名单化**——只允许预先声明的设备注解通过

**从真实源码抽象出的审计方法论**

基于以上真实源码分析，我总结出一个可操作的审计清单：

```js
审计清单：容器运行时边缘功能安全审查  
───────────────────────────────────────  
□ 1. 找到边缘功能的完整调用链  
    入口 → gRPC 处理 → 业务逻辑 → 系统调用  
    比如：CRI CreateContainer → Checkpoint/Restore → runc → CRIU  

□ 2. 标记所有"数据格式转换点"  
    protobuf ↓ Go struct → JSON → 文件系统（每个转换都是攻击面）  
    例如：CheckpointOptions.ImagePath 从 protobuf 到文件操作  

□ 3. 追踪"路径型字段"的完整生命周期  
    来自外部输入的路径 → 拼接/传递 → 文件系统操作  
    关键问题：是否做了路径合法性检查？（禁止 .. 、禁止符号链接等）  

□ 4. 检查每个"反序列化入口"的输入验证  
    tarball 解包 → checkpointArchiveEntryAllowed 存在吗？  
    JSON 反序列化 → 是否有类型/范围校验？  
    protobuf Any 类型 → typeurl.UnmarshalTo 后的字段做验证了吗？  

□ 5. 验证"信任链断裂点"  
    镜像配置 → 容器配置 → 宿主机操作  
    每个箭头处：是否重新验证了数据？还是盲目信任了上游？
```

这四个模式覆盖了 2026 年 7 个 CVE 中 6 个的根因。在 code review 时按清单逐个排查，即使不懂 containerd 全部代码，也能高效发现漏洞。

### 5.5 延伸到 CRI 实现的安全研究

containerd 不是唯一有这类问题的 CRI 实现。CRI-O、Podman 等也实现了类似的 checkpoint/restore 功能。如果你要做安全研究，以下几个方向值得关注：

**方向一：不同 CRI 实现的 checkpoint 安全差异**

同样的 checkpoint/restore 功能在 containerd、CRI-O、Podman 中的实现不同。这给了一个横向对比的机会——如果 containerd 在某个点上出了问题，其他实现大概率也有类似问题。

**方向二：kubelet 与 CRI 之间的信任边界**

kubelet 对 CRI 接口的调用是否经过了充分的验证？某些攻击者可以直接向 CRI socket 发送请求绕过 kubelet 的校验。如果攻击者已经获得了节点上的非 root 权限，但没有权限访问 CRI socket，他能不能通过竞争条件或符号链接攻击来绕过权限检查？这个方向的研究目前非常少。

**方向三：CRIU 本身的安全性**

containerd 的 checkpoint/restore 底层依赖 CRIU。CRIU 本身是一个用 C 写的复杂工具，涉及 ptrace、内存转储、进程冻结等底层操作。CRIU 的代码量在 10 万行级别，主要处理进程状态序列化和反序列化。历史上 CRIU 确实出过一些安全漏洞，比如 CVE-2022-1433（竞争条件）和 CVE-2023-2019（权限绕过）。如果 CRIU 本身有漏洞，那么所有依赖它的运行时都会受影响。这个方向值得深入研究。

## 六、技术拓展：从 containerd 到整个云原生运行时

### 6.1 CRIU 通信机制深度分析

理解 CRIU 如何被调用，是理解整个 checkpoint 攻击面的基础。containerd 并不直接调用 CRIU——调用链是这样的：

```js
containerd CRI 插件  
  → containerd-shim-runc-v2 (gRPC)  
    → runc library (Go 库)  
      → CRIU 二进制 (swrk 模式, socketpair protobuf)  
        → ptrace 冻结进程  
        → 转储内存页 (/proc/PID/mem)  
        → 保存文件描述符状态  
        → 保存设备映射
```

**关键发现：runc 与 CRIU 之间通过自定义 protobuf 协议通信。**

在 `libcontainer/criu_linux.go` 中，`criuSwrk()` 函数是核心：

```js



func criuSwrk(process \*Process, opts \*CriuOpts, ...) error {  
    
    
    
    

    
    
}
```

CRIU swrk 模式意味着 CRIU 是一个常驻进程，接收 protobuf 格式的 RPC 请求。请求中携带了所有操作参数（镜像路径、设备映射、namespaces 等）。**如果 runc 在构造 CRIU 请求时未对参数做安全校验，恶意数据就会直接传递给 CRIU 执行。**

从安全角度看，这条通信链路有几个天然弱点：

1.  **protobuf 消息全部在用户空间传输**——没有内核隔离
2.  **criu swrk 进程以 root 运行**——任何传递给它的参数都会以最高权限执行
3.  **CRIU 处理的数据格式是自描述二进制**——难以做静态分析
4.  **断点续传式的增量 dump**——父镜像与子镜像之间的依赖关系增加了攻击面复杂度

### 6.2 runc shim 状态机的安全边界

runc v2 shim 使用状态机管理容器生命周期。这个状态机的设计直接影响哪些操作在哪些状态下是允许的。

状态定义在 `cmd/containerd-shim-runc-v2/process/init_state.go` 中：

```js
                    ┌─────────────┐  
                    │  created    │  
                    └──────┬──────┘  
                           │ Start()  
                    ┌──────▼──────┐  
              ┌─────│  running    │ ◄────┐  
              │     └──────┬──────┘      │  
              │            │ Pause()     │ Resume()  
              │     ┌──────▼──────┐      │  
              │     │  paused     │──────┘  
              │     └──────┬──────┘  
              │            │  
         Checkpoint()      │  
              │     ┌──────▼──────┐  
              └─────│checkpointed │ (状态已保存，进程仍在运行/已退出)  
                    └──────┬──────┘  
                           │ Delete()  
                    ┌──────▼──────┐  
                    │  deleted    │  
                    └─────────────┘
```

**安全含义：** `Checkpoint()` 操作在 `running` 和 `paused` 状态下是允许的。但 checkpoint 执行时，CRIU 冻结进程、转储内存，这个过程中**进程的代码和数据都被序列化到磁盘**。这意味着：

1.  如果攻击者能触发 checkpoint，就可以在任意时间点捕获进程的完整内存状态
2.  被 checkpoint 的进程如果是 init 进程（PID 1），其所有子进程的状态也会被保存
3.  即使容器被暂停（paused），checkpoint 仍然可以执行——攻击者可以在容器无感知的情况下保存状态

从防护角度看，这意味着：

-   生产环境的容器运行时应该**限制 checkpoint 的调用权限**，仅允许管理员操作
-   对敏感容器（如处理用户数据的 Pod），应该**禁用 checkpoint 功能**
-   即使容器处于暂停状态，也不意味着它不能被 checkpoint

### 6.3 从 RunC 到 CRIU 的参数传递漏洞面

在 `libcontainer/criu_linux.go` 中的 `Checkpoint` 方法中，CRIU 参数设置涉及大量内核接口操作：

```js

func (c \*Container) Checkpoint(criuOpts \*CriuOpts) error {  
    
    if c.criuVersion < 3 {  
        return fmt.Errorf("CRIU version %d is too old", c.criuVersion)  
    }  

    
    req.Opts.ImagesDirFd = ...     
    req.Opts.Pid = ...              
    req.Opts.LogLevel = ...         
    req.Opts.CpuCap = ...           
    req.Opts.ExecCmd = ...          
    req.Opts.Ext = ...              

    
    req.Opts.LeaveRunning = criuOpts.LeaveRunning  
    req.Opts.TcpEstablished = criuOpts.TcpEstablished  
    req.Opts.ExtUnixSk = criuOpts.ExternalUnixConnections  
    req.Opts.FileLocks = criuOpts.FileLocks  
    req.Opts.EmptyNs = criuOpts.EmptyNs  
    req.Opts.AutoDedup = criuOpts.AutoDedup  
    req.Opts.LazyPages = criuOpts.LazyPages  
    req.Opts.StatusFd = criuOpts.StatusFd  

    
    return criuSwrk(process, criuOpts, ...)  
}
```

每个从 `CriuOpts` 直接复制到 CRIU 请求中的字段都是一个潜在的漏洞点。特别是 `Ext`（扩展选项）字段——如果扩展选项中允许自定义执行命令或路径，攻击者就能在 CRIU 的上下文中执行任意操作。

### 6.4 K8s + containerd 的信任模型分析

Checkpoint 漏洞暴露了 K8s 与 containerd 之间的信任模型问题：

```js
K8s 视角：  
  kubelet 工作负载 → 通过 CRI gRPC 调用 containerd → 执行容器操作  
  ↑ 信任: kubelet 通过 RBAC+Admission Control 验证了请求合法性  

containerd 视角：  
  接收 CRI 请求 → 解析镜像 → 读写文件系统 → 启动进程  
  ↑ 信任: containerd 信任 kubelet 传递的所有参数  

实际信任链断裂点：  
  kubelet 信任了镜像仓库 → 镜像仓库信任了镜像上传者 → 镜像中的标签等于攻击者控制  
  → 攻击者利用镜像标签 → 经过 kubelet(不验证) → 到 containerd(不验证) → 执行恶意操作
```

这个信任链中存在两个断裂点：

1.  **kubelet 不做镜像内容的深度检查**——它信任镜像仓库的签名（如果有的话）
2.  **containerd 不做输入参数的二次校验**——它信任 kubelet 传递的 CRI 参数

修复方案应该是"零信任"式的：containerd 应该**对所有来自 CRI 请求的输入做独立校验**，特别是路径型字段和设备注解。当前补丁（白名单 + 路径校验）部分解决了问题，但理想的方案是在 containerd 内部增加独立于 kubelet 的安全校验层。目前 containerd 仍处于逐个漏洞修补的阶段，距离系统化的安全设计还有距离。

### 6.5 横向对比：CRI-O 与 Podman 的 checkpoint 实现

containerd 的 checkpoint 漏洞并非孤例。CRI-O 和 Podman 同样实现了基于 CRIU 的 checkpoint/restore。

**CRI-O 的 checkpoint 实现：**

-   CRI-O 使用容器存储库的 checkpoint/restore 抽象层
-   checkpoint 功能通过 `crio checkpoint/restore` 子命令暴露
-   与 containerd 不同的是，CRI-O 对 checkpoint 镜像做了更严格的命名空间隔离

**Podman 的 checkpoint 实现：**

-   Podman 直接暴露 `podman container checkpoint/restore` 命令
-   支持 `--export` 将 checkpoint 导出为 OCI 镜像
-   Podman 在 checkpoint/restore 中增加了更多安全选项（`--ignore-static-ip`、`--ignore-static-mac` 等）

从安全角度看，三个实现共享相同的底层依赖（CRIU），因此 CRIU 本身的漏洞会影响所有实现。但它们在 **上层处理 checkpoint 数据的方式**上各有不同——这决定了包含相同 CVE 类别的风险敞口。

## 七、实战应用：攻击链构造与检测防御

### 7.1 完整攻击链构造

结合上文分析的四个关键 CVE，我们可以构造一条完整的攻击链。以 K8s 环境为例：

**阶段一：信息收集（利用 CVE-2026-53489）**

攻击者首先需要在目标节点上创建一个恶意 Pod，或者通过供应链攻击将恶意镜像投递到目标环境中。

攻击步骤：

1.  攻击者构造一个 OCI 镜像，在镜像配置或 checkpoint tarball 中插入指向 `/var/lib/kubelet/config.yaml` 和 `/etc/kubernetes/pki/ca.crt` 的符号链接
2.  镜像被拉取到目标节点后，攻击者触发容器创建/恢复操作
3.  containerd 在处理 checkpoint 恢复时跟随符号链接，将宿主机文件内容读入容器
4.  攻击者从容器内部读取泄露的 kubelet 配置和集群 CA 证书

```js
攻击者 Pod               宿主机  
    │                       │  
    │  1. 创建容器           │  
    │──────────────────────►│  
    │  2. checkpoint 恢复   │  
    │                       │──► 跟随符号链接  
    │                       │──► 读取 /etc/kubernetes/pki/ca.crt  
    │  3. 泄露的数据        │──► 读取 /var/lib/kubelet/config.yaml  
    │◄──────────────────────│  
    │                       │  
    │  4. 获取 kubelet 凭证 │  
    │  5. 向 API Server 认证│
```

**阶段二：权限提升（利用 CVE-2026-53492）**

有了 kubelet 凭证后，攻击者可以通过 CRI API 直接向 containerd 发送请求，创建一个新的容器并注入宿主机设备：

1.  攻击者构造一个修改过的 checkpoint 镜像，设备注解中增加了 `/dev/sda` 和 `/var/run/docker.sock`
2.  通过 CRI API 调用 containerd 的 `CRImportCheckpoint` 接口恢复该容器
3.  containerd 在补丁前版本中不做设备注解验证，直接传递给 runc
4.  容器恢复后，攻击者容器内部拥有了宿主机的磁盘访问权限

```js
攻击者                      containerd  
    │                           │  
    │  CRI CreateContainer      │  
    │  (带恶意设备注解)          │  
    │──────────────────────────►│  
    │                           │──► 不验证设备注解  
    │                           │──► 传递给 runc  
    │                           │──► runc 创建设备节点  
    │                           │──► 容器获得 /dev/sda 访问权限  
    │                           │  
    │  Pod 正常运行              │  
    │◄──────────────────────────│  
    │                           │  
    │  mount /dev/sda /mnt      │  
    │  → 读取同一节点其他租户数据│
```

**阶段三：远程代码执行（利用 CVE-2026-53488 或 CVE-2026-50195）**

最终阶段，攻击者使用标签传播漏洞或镜像缓存投毒在宿主机上执行任意代码：

**场景 A：标签传播 RCE** 攻击者创建一个恶意容器，在 Dockerfile 的 LABEL 中嵌入命令注入 payload：

```js
FROM alpine:latest  
LABEL io.containerd.runc.v2.execute="|| echo 'attacker' >> /etc/passwd"
```

**场景 B：缓存投毒 + 被动触发** 攻击者利用 CVE-2026-50195 污染节点的镜像缓存，将合法镜像名指向恶意内容。当管理员部署新的工作负载时，触发恶意代码执行：

```js
\# 攻击者通过已被突破的节点  
\# 或通过供应链投毒，导入恶意 checkpoint 镜像  
ctr image import malicious-checkpoint.tar.gz  
\# 恶意镜像的名称为 "docker.io/library/nginx:latest"  
\# 本地缓存被投毒，后续的 nginx 部署会使用恶意镜像
```

完整攻击链的时序图：

```js
时间线  
  │  
  ├─ T1: 攻击者通过符号链接泄露读取 kubelet 凭证 (CVE-2026-53489)  
  │  
  ├─ T2: 利用凭证通过 CRI API 发起设备注入 (CVE-2026-53492)  
  │    └─ 获得宿主机磁盘和 Docker socket 访问权限  
  │  
  ├─ T3a: 通过标签传播在宿主机执行命令 (CVE-2026-53488)  
  │    └─ 建立持久化后门  
  │  
  ├─ T3b: 通过镜像缓存投毒污染节点 (CVE-2026-50195)  
  │    └─ 等待管理员部署触发  
  │  
  └─ T4: 横向移动 → 利用节点凭证攻击集群中的其他节点
```

### 7.2 检测规则

以下检测规则可用于识别 checkpoint 相关的攻击行为。

**Falco 规则：检测异常的 checkpoint 操作**

```js
\# falco\_rules\_checkpoint.yaml  
\# 检测非预期的容器 checkpoint 操作  
\- rule: Unauthorized Container Checkpoint  
  desc: detect unexpected container checkpoint operations via CRIU  
  condition: >  
    spawned\_process and  
    proc.name = criu and  
    proc.args contains "dump" and  
    not proc.args contains "shell-job"  
  output: >  
    Unauthorized checkpoint detected (user=%user.name pid=%proc.pid  
    command=%proc.cmdline container=%container.id)  
  priority: CRITICAL  
  tags: \[container, persistence, checkpoint\]  

\- rule: Checkpoint Image Import  
  desc: detect checkpoint image import operations  
  condition: >  
    spawned\_process and  
    proc.name = containerd and  
    proc.args contains "image import" and  
    container.id != host  
  output: >  
    Checkpoint image import from container (user=%user.name  
    pid=%proc.pid container=%container.id)  
  priority: WARNING  
  tags: \[container, image, checkpoint\]
```

**Tracee eBPF 检测规则**

```js
\# Tracee 规则：检测符号链接遍历  
tracee --trace event=do\_symlinkat --trace event=security\_inode\_symlink  
       --trace event=do\_splice --trace event=vfs\_read  
       --capture write=/tmp/tracee-output  

\# 监控特定的文件路径访问模式  
tracee --trace event=vfs\_read --trace path=/etc/shadow  
       --trace event=vfs\_read --trace path=/var/lib/kubelet/config.yaml
```

**K8s Audit 日志检测：异常的 checkpoint API 调用**

```js
\# k8s 审计规则：检测 CRI checkpoint 调用  
\- level: Request  
  resources:  
    - group: ""  # core API group  
      resources: \["pods"\]  
  verbs: \["create", "update"\]  
  annotations:  
    - key: "response.status"  
      expression: "contains(response.status, 'Checkpoint')"
```

**节点级文件监控**

```js
\# 监控 checkpoint 目录的异常文件创建  
inotifywait -m -r -e create,modify /var/lib/containerd/checkpoint/ |  
while read path action file; do  
    echo "\[ALERT\] Checkpoint file change detected: $path$file ($action)"  
done  

\# 监控 CRIU 镜像文件  
inotifywait -m -r -e create /var/lib/containerd/io.containerd.runc.v2/ |  
    grep -E "criu-dump|criu-work|checkpoint"
```

### 7.3 防御配置

**方案一：OPA/Gatekeeper 策略限制 checkpoint 操作**

```js
\# opa\_checkpoint\_restriction.yaml  
apiVersion: templates.gatekeeper.sh/v1  
kind: ConstraintTemplate  
metadata:  
  name: k8srestrictcheckpoint  
spec:  
  crd:  
    spec:  
      names:  
        kind: K8sRestrictCheckpoint  
  targets:  
    - target: admission.k8s.gatekeeper.sh  
      rego: |  
        package k8srestrictcheckpoint  

        violation\[{"msg": msg}\] {  
          # 检查是否使用了 checkpoint 类型的镜像  
          # 或试图创建需要特权模式的容器  
          input.request.kind.kind == "Pod"  
          container := input.request.object.spec.containers\[\_\]  
          # 检测镜像是否为 checkpoint 类型  
          annotations := input.request.object.metadata.annotations  
          annotations\["checkpoint.opencontainers.org/checkpoint"\] == "true"  
          msg := sprintf("Checkpoint image usage is restricted: %v", \[container.image\])  
        }
```

**方案二：Kyverno 策略限制特权容器**

```js
\# kyverno\_restrict\_checkpoint.yaml  
apiVersion: kyverno.io/v1  
kind: ClusterPolicy  
metadata:  
  name: restrict-checkpoint  
spec:  
  validationFailureAction: Enforce  
  rules:  
    - name: no-checkpoint-containers  
      match:  
        any:  
          - resources:  
              kinds:  
                - Pod  
      validate:  
        message: "Checkpoint containers and privileged containers with checkpoint capabilities are not allowed."  
        deny:  
          conditions:  
            any:  
              - key: "{{ request.object.metadata.annotations.\\"checkpoint.opencontainers.org/checkpoint\\" }}"  
                operator: Equals  
                value: "true"
```

**方案三：Seccomp 策略限制 CRIU 系统调用**

```js
{  
  "defaultAction": "SCMP\_ACT\_ERRNO",  
  "architectures": \["SCMP\_ARCH\_X86\_64", "SCMP\_ARCH\_AARCH64"\],  
  "syscalls": \[  
    {  
      "names": \["ptrace", "process\_vm\_readv", "process\_vm\_writev"\],  
      "action": "SCMP\_ACT\_ALLOW",  
      "includes": {  
        "minKernelVersion": "4.8"  
      }  
    }  
  \]  
}
```

注意：这个 seccomp 策略是针对**容器的**，不是针对 CRIU 本身的。它的作用是不让普通容器使用 ptrace——CRIU 本身在宿主机上运行，不受这个策略限制。正确的做法是在节点层面使用 AppArmor/SELinux 策略限制 CRIU 的行为。

**方案四：节点级 AppArmor 策略限制 CRIU**

```js
\# apparmor-criudump  
abi <abi/4.0>,  
include <tunables/global>  

profile criu-dump /usr/sbin/criu flags=(attach\_disconnected) {  
  include <abstractions/base>  
  include <abstractions/nameservice>  

  # 限制 CRIU 只能访问指定目录  
  /var/lib/containerd/checkpoint/\*\* rw,  
  /var/lib/containerd/io.containerd.runc.v2/\*\* rw,  

  # 禁止 CRIU 写入未授权的目录  
  deny /etc/\*\* w,  
  deny /var/lib/kubelet/\*\* w,  

  # 限制 ptrace 范围  
  ptrace (read, trace) peer=/usr/bin/containerd-shim-runc-v2,  
  ptrace (read, trace) peer=/usr/bin/containerd,  

  # 网络  
  network inet tcp,  
  network unix,  
}
```

**方案五：运行时配置限制**

```js
\# /etc/containerd/config.toml  
\# 限制 checkpoint 相关的操作  

disabled\_plugins = \[\]  
\# 注意：containerd 没有直接的 "disable checkpoint" 配置项  
\# 需要通过插件级别或权限控制来限制  

\# 推荐的缓解措施：  
\# 1. 升级到修复版本  
\# 2. 在 K8s 层面禁止非管理员创建 Pod  
\# 3. 使用 Pod Security Standards 的 Baseline 或 Restricted 模式  
\# 4. 监控 CRI socket 的访问
```

### 7.4 自动化漏洞验证脚本

以下脚本可用于验证 containerd 是否受到 checkpoint 相关漏洞影响：

```js
#!/bin/bash  
\# check\_containerd\_checkpoint\_vulns.sh  
\# 用途：验证 containerd 是否受到 2026 年 checkpoint 漏洞影响  

echo "\[\*\] Checking containerd version..."  
CONTAINERD\_VERSION=$(containerd --version 2>/dev/null || ctr version 2>/dev/null | head -1)  
echo "    Found: $CONTAINERD\_VERSION"  

\# 检查 CRIU 是否可用  
echo "\[\*\] Checking CRIU availability..."  
if command -v criu &> /dev/null; then  
    CRIU\_VERSION=$(criu --version | head -1)  
    echo "    CRIU available: $CRIU\_VERSION"  
else  
    echo "    \[!\] CRIU not found — checkpoint likely disabled"  
fi  

\# 检查 ptrace\_scope  
echo "\[\*\] Checking ptrace\_scope..."  
if \[ -f /proc/sys/kernel/yama/ptrace\_scope \]; then  
    SCOPE=$(cat /proc/sys/kernel/yama/ptrace\_scope)  
    echo "    ptrace\_scope = $SCOPE"  
    if \[ "$SCOPE" -gt 1 \]; then  
        echo "    \[!\] ptrace\_scope > 1 — checkpoint may fail due to ptrace restrictions"  
    fi  
fi  

\# 检查 containerd 配置中的 checkpoint 相关设置  
echo "\[\*\] Checking containerd config for checkpoint related settings..."  
CONFIG\_PATH=${CONTAINERD\_CONFIG:-/etc/containerd/config.toml}  
if \[ -f "$CONFIG\_PATH" \]; then  
    if grep -qi "checkpoint\\|criu" "$CONFIG\_PATH" 2>/dev/null; then  
        echo "    \[!\] Config contains checkpoint/CRIU references — checkpoint may be enabled"  
    else  
        echo "    No explicit checkpoint config found (default behavior)"  
    fi  
else  
    echo "    Config file not found at $CONFIG\_PATH"  
fi  

\# 检查是否有可能在运行 checkpointed 容器  
echo "\[\*\] Checking for checkpointed container states..."  
if \[ -d /var/lib/containerd/ \]; then  
    CP\_COUNT=$(find /var/lib/containerd/ -name "checkpoint" -type d 2>/dev/null | wc -l)  
    echo "    Found $CP\_COUNT checkpoint directories"  
fi  

echo ""  
echo "\[\*\] Summary:"  
echo "    Containerd version: $CONTAINERD\_VERSION"  
echo "    CRIU: $(command -v criu &>/dev/null && echo 'available' || echo 'not available')"  
echo "    Checkpoint enabled: $(command -v criu &>/dev/null && \[ $(cat /proc/sys/kernel/yama/ptrace\_scope 2>/dev/null || echo 2) -le 1 \] && echo 'likely' || echo 'likely disabled')"  

echo ""  
echo "\[!\] Manual verification steps:"  
echo "    1. Check if you're running a vulnerable version (containerd < 2.2.5)"  
echo "    2. Test with: ctr task checkpoint --container-name <container>"  
echo "    3. Monitor audit logs for unexpected checkpoint operations"  
echo "    4. Review container image labels for suspicious content"
```

### 7.5 应急响应流程

当检测到可疑的 checkpoint 操作时，建议按以下流程响应：

```js
1\. 确认检测  
   └─ 检查 k8s 审计日志 → 确认是合法运维操作还是异常行为  

2\. 隔离受影响节点  
   └─ kubectl cordon <node>  
   └─ kubectl drain <node> --ignore-daemonsets  
   └─ 如果怀疑节点已失陷，优先使用网络隔离而非 drain  

3\. 取证分析  
   └─ 收集 /var/lib/containerd/ 下的异常 checkpoint 文件  
   └─ 收集容器镜像标签和注解内容  
   └─ 检查 /etc/shadow、kubelet 配置等敏感文件的访问日志  
   └─ 使用 falco/tracee 回顾 checkpoint 操作的时间线  

4\. 修复  
   └─ 升级 containerd 到修复版本  
   └─ 轮换泄露的凭证（CA 证书、Service Account token）  
   └─ 在所有节点上执行恶意镜像扫描  

5\. 复盘  
   └─ 分析攻击入口（供应链投毒 / 凭证泄露 / 配置错误）  
   └─ 更新检测规则  
   └─ 补充 OPA/Kyverno 策略
```

## 八、总结

2026 年 6 月份集中发布的 7 个 containerd CVE，涉及宿主机 RCE（CVE-2026-53488）、跨 Pod RCE（CVE-2026-50195）、设备隔离绕过（CVE-2026-53492）、符号链接信息泄露（CVE-2026-53489），以及三个 DoS 漏洞。

这些漏洞的核心联系是：**容器检查点（checkpoint/restore）功能的安全审查不足**。这是一个典型的"功能先上线、安全后补课"的案例。从更宏观的角度看，这反映了云原生生态系统中一个普遍问题：功能开发和性能优化被优先考虑，安全审查是后补的。对于 containerd 这种基础设施级别的组件，这个问题尤其严重，因为它的安全漏洞会扩散到所有依赖它的上层系统。

从防御角度看，如果你的 K8s 集群用到了容器检查点或热迁移功能，建议：

-   检查 containerd 版本，确认是否修复了上述 CVE
-   限制 checkpoint/restore 权限，非必要不给
-   在镜像准入控制中增加对可疑标签和注解的校验

从研究角度看，边缘功能审计是一个被低估的方向。容器运行时的核心路径经过多年打磨已经比较成熟，但边缘功能（checkpoint、热迁移、设备注入）的安全审查还很初级。这个判断不仅适用于 containerd，也适用于 CRI-O、Podman、Kata Containers 等其他容器运行时。如果你在找一个高 ROI 的安全研究方向，我强烈推荐容器运行时的边缘功能审计。在这个方向上，投入一两个月的时间很可能产出三到四个严重级别的 CVE。对比一下，在 Web 安全方向上花同样的时间，产出大概率没有这么集中。

**说实话，2026 年关于容器运行时的安全研究，最值得花时间的地方不是找新的逃逸方式，而是把那些"没人认真审查过"的边缘功能从头到尾过一遍。** containerd 在 2026 年上半年一共集中修了 7 个 CVE 漏洞，其中 4 个是严重/高危。这个数字不是巧合——它反映的是一个规律：容器运行时的新功能从上线到被充分审查之间存在一个"安全窗口期"，这个窗口期通常长达一到两年。2026 年修的这些漏洞，对应的代码大概率是在 2024-2025 年写的。说白了，当功能开发完成后，它的安全隐患还需要一两年才会被发现和修复。这段时间就是攻击者可以利用的窗口。

从攻击者的视角来看，容器运行时的核心路径越来越难打，是因为该修的漏洞大部分已经修了。但每一次新功能的引入，尤其是涉及复杂状态操作的功能（序列化、热迁移、状态恢复），都会引入新的攻击面。而这些攻击面，通常只有几个月的"免检窗口"——在功能发布和安全审查完成之间。

一个具体的操作建议：关注 containerd 的 GitHub 仓库中打上了 "feature" 标签的 PR，特别是涉及新的 gRPC 接口、新的镜像处理路径、新的状态管理逻辑的变更。这些 PR 合入后的 6-12 个月是最佳审计窗口。

从更广的视角看，容器运行时的安全审计应该从"漏洞驱动"转向"功能驱动"。漏洞驱动的审计是被动的——等待 CVE 报告出来才去修。功能驱动的审计是主动的——在新功能发布后主动审查其安全性。对于 containerd 这种广泛部署的组件，功能驱动审计的价值远高于走马观花地扫描已知漏洞。

这扇窗口，就是安全研究的机会。对于 2026 年的容器安全研究员来说，最有效的策略就是：**盯住每个容器运行时的新功能发布，在功能上线的 12-18 个月内重点审计它的边缘路径。**

我把这个策略称为"延迟审计法"——不是等漏洞报告了再补，而是在功能代码稳定之后、但还没有被大规模部署之前，主动去审计它的边界情况。containerd 的 checkpoint/restore 功能在 v1.7（2023 年）中引入，2026 年才被发现有问题，中间隔了将近 3 年。如果你在 2024 年就开始审计这个功能，你可能是发现这些漏洞的人。

从实战的角度来看，这波 containerd 漏洞的攻击链路可以有多种组合方式。最简单的攻击场景：攻击者先用 CVE-2026-53489 的符号链接泄露读取宿主机上的 kubelet 配置和 Service Account token，然后用 CVE-2026-53492 的设备注入把宿主机根目录挂载进容器，最后用 CVE-2026-53488 或 CVE-2026-50195 在宿主机上执行任意代码。一条完整的攻击链，涉及三个不同的漏洞，覆盖了信息收集、权限提升、代码执行三个关键环节。

更隐蔽的攻击场景：攻击者利用 CVE-2026-50195 的镜像缓存投毒，等待运维人员部署新的工作负载，让运维人员自己的部署操作触发恶意代码的执行。这种情况下，攻击者甚至不需要直接在受害者的宿主机上留下痕迹，因为代码执行是通过"合法"的容器创建路径触发的。

从供应链的角度来看，containerd 的这波漏洞也提出了一个新的问题：当 K8s 已经成为云原生的事实标准，containerd 成为默认运行时，它的安全就直接决定了整个云原生生态的安全水位。如果一个 containerd RCE 漏洞被大规模利用，影响范围可能覆盖全球大部分 K8s 集群。这不是某个特定云厂商的问题，而是整个行业的基础设施安全问题。一个 containerd 的 RCE 漏洞可以影响到所有运行在 K8s 上的工作负载。这不是某个云厂商的问题，是整个行业的问题。

另外还有一个很少有人提到的点：大多数 containerd 的部署是通过发行版包管理器（apt、yum）安装的，修复版本需要等待发行版打包。从上游发布修复到下游用户真正更新，中间有数周甚至数月的延迟。对于 CVE-2026-53488 这种宿主机 RCE 漏洞，这个延迟窗口期的安全风险非常大。如果攻击者在这个窗口期内扫描到未修复的 containerd 节点，可以批量利用。对于 CVE-2026-53488 这种宿主机 RCE，这个窗口期足够攻击者大规模扫描和利用。

做安全研究的人经常面临一个问题：选一个竞争激烈的方向跟几百人抢，还是选一个冷门方向自己包场？容器运行时边缘功能审计属于后者。参与的人少、产出价值高、而且对云原生生态有实际贡献。如果你在找 2026 年下半年值得投入的安全研究方向，我的建议很明确：挑一个容器运行时的新功能，从头到尾审一遍它的边界。结果不会让你失望。
