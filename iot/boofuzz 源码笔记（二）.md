# boofuzz 源码笔记（二）
> Ayaka
> 来源：https://www.iotsec-zone.com/article/323

首先来填一个笔记（一）中忘记说的小坑：
```python
blocks.CURRENT.push(Static(name=name, default_value=value))
```
这句代码笔记（一）中只说了“实例化了一个Static类并通过push方法加入到当前blocks.CURRENT中”，但是为什么会有push方法，push方法怎么实现的忘记说了，这里补充一下

首先blocks.CURRENT这个东西在s_initialize中我们是见过的：
```python
def s_initialize(name):
	if name in blocks.REQUESTS:
        raise exception.SullyRuntimeError("blocks.REQUESTS ALREADY EXISTS: %s" % name)
    blocks.REQUESTS[name] = Request(name)
    blocks.CURRENT = blocks.REQUESTS[name]
```
所以blocks.CURRENT是一个Request类实例化出来的一个对象，push函数方法也实现在其中，跟进看一下源码：
```python
class Request(FuzzableBlock, Node):
    """Top level container. Can hold any block structure or primitive.

    This can essentially be thought of as a super-block, root-block, daddy-block or whatever other alias you prefer.

    """
```
Request类是一个顶层的容器，其中实现了push方法：
```python
def push(self, item):
        """
        Push an item into the block structure. If no block is open, the item goes onto the request stack. otherwise,
        the item goes onto the last open blocks stack.
        """
        item.context_path = self._generate_context_path(self.block_stack)
        item.request = self
        # ensure the name doesn't already exist.
        if item.qualified_name in list(self.names):
            raise exception.SullyRuntimeError("BLOCK NAME ALREADY EXISTS: %s" % item.qualified_name)

        self.names[item.qualified_name] = item

        # if there are no open blocks, the item gets pushed onto the request stack.
        # otherwise, the pushed item goes onto the stack of the last opened block.
        if not self.block_stack:
            self.stack.append(item)
        else:
            self.block_stack[-1].push(item)

        # add the opened block to the block stack.
        if isinstance(item, FuzzableBlock):
            self.block_stack.append(item)
```
首先确认name是否在names字典中出现过，如果出现过则抛出异常，没有出现过的话则将item放进names字典中。判断是否有block_stack，如果有的话则将当前item加入到最后一个打开的block中，如果没有的话则直接加入到stack中，block_stack和stack都是列表数据结构，定义在init中：
```python
def __init__(self, name=None, children=None):
        FuzzableBlock.__init__(self, name=name, request=self)
        Node.__init__(self)
        self.label = name  # node label for graph rendering.
        self.stack = []  # the request stack.
        self.block_stack = []  # list of open blocks, -1 is last open block.
        self.callbacks = collections.defaultdict(list)
        self.names = {name: self}  # dictionary of directly accessible primitives.
        self._rendered = b""  # rendered block structure.
        self._mutant_index = 0  # current mutation index.
        self._element_mutant_index = None  # index of current mutant element within self.stack
        self.mutant = None  # current primitive being mutated
```

继续关注这句话：
```python
blocks.CURRENT.push(Static(name=name, default_value=value))
```
彻底弄懂了blocks.CURRENT.push之后，我们来关注一下Static(name=name, default_value=value)究竟做了什么

```python
class Static(Fuzzable):
    """Static primitives are fixed and not mutated while fuzzing.

    :type name: str, optional
    :param name: Name, for referencing later. Names should always be provided, but if not, a default name will be given,
        defaults to None
    :type default_value: Raw, optional
    :param default_value: Raw static data
    """

    def __init__(self, name=None, default_value=None, *args, **kwargs):
        super(Static, self).__init__(name=name, default_value=default_value, fuzzable=False, *args, **kwargs)

    def encode(self, value, mutation_context):
        if value is None:
            value = b""
        return helpers.str_to_bytes(value)
```

从注释中的描述可以看出，static原语在fuzzing的过程中不会发生变异,在static的init中可以看到，它直接通过super方法调用了父类fuzzable的init函数，并且传入参数的时候指定了fuzzable=False,其余参数如name等原封不动传入。之前说static实例化出来的对象在fuzzing过程中不参与变异，就是通过在调用父类init的时候指定fuzzable参数为固定的False实现的。

所以接下来要去看看fuzzable类是如何实现的：
```python
class Fuzzable(object):
    """Parent class for all primitives and blocks.
```

在fuzzable开头就说明了，这是所有原语和block的父类。
接着来看init：
```python
def __init__(self, name=None, default_value=None, fuzzable=True, fuzz_values=None):
        self._fuzzable = fuzzable
        self._name = name
        self._default_value = default_value
        self._context_path = ""
        self._request = None
        self._halt_mutations = False
        if fuzz_values is None:
            fuzz_values = list()
        self._fuzz_values = fuzz_values

        if self._name is None:
            Fuzzable.name_counter += 1
            self._name = "{0}{1}".format(type(self).__name__, Fuzzable.name_counter)
```

进行了一系列赋值操作，并且通过计数器为每个对象分配一个独一无二的编号。

看到这里，已经将s_static函数的源码看完了，我们梳理一下当我们写下一个s_static，boofuzz里究竟发生了什么：

首先我们肯定已经至少写过一次s_initialize，所以blocks.CURRENT应该是某一个Request类实例化出的对象，而不是空。并且打开了一个block，即此时blocks.CURRENT里的block_stack应该不为空，至少有一个block

然后通过Static类调用super函数最终调用了fuzzable类的实例化出了一个对象，这个对象通过Request类中实现的push方法添加到最新选择的block中。

接下来再来简要分析几个常用原语
**s_string**:
```python
def s_string(value="", size=None, padding=b"\x00", encoding="ascii", fuzzable=True, max_len=None, name=None):
    """
    Push a string onto the current block stack.

    :type  value:    str
    :param value:    (Optional, def="")Default string value
    :type  size:     int
    :param size:     (Optional, def=None) Static size of this field, leave None for dynamic.
    :type  padding:  Character
    :param padding:  (Optional, def="\\x00") Value to use as padding to fill static field size.
    :type  encoding: str
    :param encoding: (Optional, def="ascii") String encoding, ex: utf_16_le for Microsoft Unicode.
    :type  fuzzable: bool
    :param fuzzable: (Optional, def=True) Enable/disable fuzzing of this primitive
    :type  max_len:  int
    :param max_len:  (Optional, def=None) Maximum string length
    :type  name:     str
    :param name:     (Optional, def=None) Specifying a name gives you direct access to a primitive
    """
    # support old interface where default was -1 instead of None
    if size == -1:
        size = None
    if max_len == -1:
        max_len = None

    blocks.CURRENT.push(
        String(
            name=name,
            default_value=value,
            size=size,
            padding=padding,
            encoding=encoding,
            max_len=max_len,
            fuzzable=fuzzable,
        )
    )
```
从源码中可以看到s_string接收必选的value参数，其他参数均为可选参数，然后将参数原封不动的传入String类中进行实例化，而后用同样的手法push到block中。

String类中有一些实现变异的逻辑，我们留到session.fuzz()部分统一进行分析，这里先来看它的init函数：
```python
def __init__(
        self, name=None, default_value="", size=None, padding=b"\x00", encoding="utf-8", max_len=None, *args, **kwargs
    ):
        super(String, self).__init__(name=name, default_value=default_value, *args, **kwargs)

        self.size = size
        self.max_len = max_len
        if self.size is not None:
            self.max_len = self.size
        self.encoding = encoding
        self.padding = padding
        if isinstance(padding, six.text_type):
            self.padding = self.padding.encode(self.encoding)
        self._static_num_mutations = None
        self.random_indices = {}

        local_random = random.Random(0)  # We want constant random numbers to generate reproducible test cases
        previous_length = 0
        # For every length add a random number of random indices to the random_indices dict. Prevent duplicates by
        # adding only indices in between previous_length and current length.
        for length in self._long_string_lengths:
            self.random_indices[length] = local_random.sample(
                range(previous_length, length), local_random.randint(1, self._long_string_lengths[0])
            )
            previous_length = length
```

相比s_static，s_string中的处理明显要多一些，首先还是通过super调用父类的init，然后设置了一系列变量，其中一部分会用于后续的变异过程。然后为每一个长度添加一个随机长度的随机下标列表，用于后续的变异操作。

**s_group**:
```python
def s_group(name=None, values=None, default_value=None):
    """
    This primitive represents a list of static values, stepping through each one on mutation. You can tie a block
    to a group primitive to specify that the block should cycle through all possible mutations for *each* value
    within the group. The group primitive is useful for example for representing a list of valid opcodes.

    :type  name:            str
    :param name:            (Optional, def=None) Name of group
    :type  values:          List or raw data
    :param values:          (Optional, def=None) List of possible raw values this group can take.
    :type  default_value:   str or bytes
    :param default_value:   (Optional, def=None) Specifying a value when fuzzing() is complete
    """

    blocks.CURRENT.push(Group(name=name, default_value=default_value, values=values))
```
s_group第一个参数是作为唯一表示的name,values则是一个列表，里面是一系列可能采用的value值，这个函数在fuzz一些特征码，操作码或者可选方法中非常好用，比如http协议中常用的几个方法，get,post等等，就可以选择将其加入到一个group中，就可以实现fuzz过程中循环替换group中的字段。

```python
def __init__(self, name=None, values=None, default_value=None, encoding="ascii", *args, **kwargs):
        assert len(values) > 0, "You can't have an empty value list for your group!"
        for val in values:
            assert isinstance(val, (six.binary_type, six.string_types)), "Value list may only contain string/byte types"
        values = list(map(lambda value: value if isinstance(value, bytes) else value.encode(encoding=encoding), values))

        if default_value is None:
            default_value = values[0]

        default_value = default_value if isinstance(default_value, bytes) else default_value.encode(encoding=encoding)

        if default_value in values:
            values.remove(default_value)

        super(Group, self).__init__(name=name, default_value=default_value, *args, **kwargs)

        self.values = values
```

实例化的时候首先判断了values中的元素个数不能为0，如果为0则报错，然后检查了values中的每个元素是否为str或bytes类型，如果都不是则报错。接下来更新default_value，最后通过super方法调用父类的init函数进行最后的实例化。

最后再来看个s_delim函数：
```python
def s_delim(value=" ", fuzzable=True, name=None):
    """
    Push a delimiter onto the current block stack.

    :type  value:    Character
    :param value:    (Optional, def=" ")Original value
    :type  fuzzable: bool
    :param fuzzable: (Optional, def=True) Enable/disable fuzzing of this primitive
    :type  name:     str
    :param name:     (Optional, def=None) Specifying a name gives you direct access to a primitive
    """

    blocks.CURRENT.push(Delim(name=name, default_value=value, fuzzable=fuzzable))
```
和其他s系列函数基本相同，默认的value参数为空格，name和fuzzable字段用户都可以自定义，s_delim定义上的功能为添加一个分隔符到当前block的stack中，来看看具体实现：

```python
class Delim(BasePrimitive):
    r"""Represent a delimiter such as :,\r,\n, ,=,>,< etc... Mutations include repetition, substitution and exclusion.

    :param name: Name, for referencing later. Names should always be provided, but if not, a default name will be given,
        defaults to None
    :type name: str, optional
    :param default_value: Value used when the element is not being fuzzed - should typically represent a valid value.
    :type default_value: char, optional
    :param fuzzable: Enable/disable fuzzing of this primitive, defaults to true
    :type fuzzable: bool, optional
    """

    def __init__(self, name=None, default_value=" ", *args, **kwargs):
        super(Delim, self).__init__(name=name, default_value=default_value, *args, **kwargs)

        self._fuzz_library.append(self._default_value * 2)
        self._fuzz_library.append(self._default_value * 5)
        self._fuzz_library.append(self._default_value * 10)
        self._fuzz_library.append(self._default_value * 25)
        self._fuzz_library.append(self._default_value * 100)
        self._fuzz_library.append(self._default_value * 500)
        self._fuzz_library.append(self._default_value * 1000)

        self._fuzz_library.append("")
        if self._default_value == " ":
            self._fuzz_library.append("\t")
            self._fuzz_library.append("\t" * 2)
            self._fuzz_library.append("\t" * 100)

        self._fuzz_library.append(" ")
        self._fuzz_library.append("\t")
        self._fuzz_library.append("\t " * 100)
        self._fuzz_library.append("\t\r\n" * 100)
        self._fuzz_library.append("!")
        self._fuzz_library.append("@")
        self._fuzz_library.append("#")
        self._fuzz_library.append("$")
        self._fuzz_library.append("%")
        self._fuzz_library.append("^")
        self._fuzz_library.append("&")
        self._fuzz_library.append("*")
        self._fuzz_library.append("(")
        self._fuzz_library.append(")")
        self._fuzz_library.append("-")
        self._fuzz_library.append("_")
        self._fuzz_library.append("+")
        self._fuzz_library.append("=")
        self._fuzz_library.append(":")
        self._fuzz_library.append(": " * 100)
        self._fuzz_library.append(":7" * 100)
        self._fuzz_library.append(";")
        self._fuzz_library.append("'")
        self._fuzz_library.append('"')
        self._fuzz_library.append("/")
        self._fuzz_library.append("\\")
        self._fuzz_library.append("?")
        self._fuzz_library.append("<")
        self._fuzz_library.append(">")
        self._fuzz_library.append(".")
        self._fuzz_library.append(",")
        self._fuzz_library.append("\r")
        self._fuzz_library.append("\n")
        self._fuzz_library.append("\r\n" * 64)
        self._fuzz_library.append("\r\n" * 128)
        self._fuzz_library.append("\r\n" * 512)
```
可以看到boofuzz将一系列认为可能作为分隔符的符号加入到_fuzz_library中，并且其中一部分还做了长度扩展，如果我们在写s_deilm的时候开启了fuzzable选项，则会根据_fuzz_library里的内容进行变异。

这里也能反映出boofuzz的可扩展性，当面对一个较为具体的协议时，可以更改这里的实现方式，将一些不可能作为分隔符的符号从_fuzz_library中去掉，如果有分隔符不在这里的也可以手动添加进去，从而提高fuzzing的准确性和效率。

接下来看这行代码：
```python
session.connect(s_get("Request"))
```
先来看s_get是如何实现的
```python
def s_get(name=None):
    """
    Return the request with the specified name or the current request if name is not specified. Use this to switch from
    global function style request manipulation to direct object manipulation. Example::

        req = s_get("HTTP BASIC")
        print(req.num_mutations())

    The selected request is also set as the default current. (ie: s_switch(name) is implied).

    :type  name: str
    :param name: (Optional, def=None) Name of request to return or current request if name is None.

    :rtype:  blocks.Request
    :return: The requested request.
    """

    if not name:
        return blocks.CURRENT

    # ensure this gotten request is the new current.
    s_switch(name)

    if name not in blocks.REQUESTS:
        raise exception.SullyRuntimeError("blocks.REQUESTS NOT FOUND: %s" % name)

    return blocks.REQUESTS[name]
```

在s_get中，name不是一个必选参数，可以为空，如果为空的话，则直接返回当前Request，如果不为空的话，则首先调用s_switch函数，将name对应的Request切换到blocks.CURRENT上。然后判断name是否在blocks.REQUESTS中，如果不在则抛出异常，如果在的话则直接返回name对应的Request。

接下来看看session.connect是如何实现的：
```python
def connect(self, src, dst=None, callback=None):
        """
        Create a connection between the two requests (nodes) and register an optional callback to process in between
        transmissions of the source and destination request. The session class maintains a top level node that all
        initial requests must be connected to. Example::

            sess = sessions.session()
            sess.connect(sess.root, s_get("HTTP"))

        If given only a single parameter, sess.connect() will default to attaching the supplied node to the root node.
        This is a convenient alias. The following line is identical to the second line from the above example::

            sess.connect(s_get("HTTP"))

        Leverage callback methods to handle situations such as challenge response systems.
        A callback method must follow the message signature of :meth:`Session.example_test_case_callback`.
        Remember to include \\*\\*kwargs for forward-compatibility.

        Args:
            src (str or Request (pgrah.Node)): Source request name or request node
            dst (str or Request (pgrah.Node), optional): Destination request name or request node
            callback (def, optional): Callback function to pass received data to between node xmits. Default None.

        Returns:
            pgraph.Edge: The edge between the src and dst.
        """
        # if only a source was provided, then make it the destination and set the source to the root node.
        if dst is None:
            dst = src
            src = self.root

        # if source or destination is a name, resolve the actual node.
        if isinstance(src, six.string_types):
            src = self.find_node("name", src)

        if isinstance(dst, six.string_types):
            dst = self.find_node("name", dst)

        # if source or destination is not in the graph, add it.
        if src != self.root and self.find_node("name", src.name) is None:
            self.add_node(src)

        if self.find_node("name", dst.name) is None:
            self.add_node(dst)

        # create an edge between the two nodes and add it to the graph.
        edge = Connection(src.id, dst.id, callback)
        self.add_edge(edge)

        return edge
```

如果给了两个参数，则在两个参数对应的两个Request中建立一条edge，如果只有一个参数，则将此Request和根节点建立一条edge。也就是说我们所创立的Request可以看做是一个一个node，而connect就是在node之间建立edge，fuzzing过程是从root node开始的，然后按照关系图的顺序向后进行。

最后来看看这行代码：
```python
session.fuzz()
```
```python
def fuzz(self, name=None, max_depth=None):
        """Fuzz the entire protocol tree.

        Iterates through and fuzzes all fuzz cases, skipping according to
        self.skip and restarting based on self.restart_interval.

        If you want the web server to be available, your program must persist
        after calling this method. helpers.pause_for_signal() is
        available to this end.

        Args:
            name (str): Pass in a Request name to fuzz only a single request message. Pass in a test case name to fuzz
                        only a single test case.
            max_depth (int): Maximum combinatorial depth; set to 1 for "simple" fuzzing.

        Returns:
            None
        """
        self.total_mutant_index = 0
        self.total_num_mutations = self.num_mutations(max_depth=max_depth)

        if name is None or name == "":
            self._main_fuzz_loop(self._generate_mutations_indefinitely(max_depth=max_depth))
        else:
            self.fuzz_by_name(name=name)
```

如果在session.fuzz调用的时候传入了name参数，则会调用fuzz_by_name：
```python
def fuzz_by_name(self, name):
        """Fuzz a particular test case or node by name.

        Args:
            name (str): Name of node.
        """
        warnings.warn("Session.fuzz_by_name is deprecated in favor of Session.fuzz(name=name).")
        path, mutations = helpers.parse_test_case_name(name)
        if len(mutations) < 1:
            self._fuzz_single_node_by_path(path)
        else:
            self.total_mutant_index = 0
            self.total_num_mutations = 1

            node_edges = self._path_names_to_edges(node_names=path)
            self._main_fuzz_loop(self._generate_test_case_from_named_mutations(node_edges, mutations))
```
fuzz_by_name函数从注释内的描述来看，是fuzzing一个特定的Request，而不是按照构建好的状态图从头fuzz。首先会通过parse_test_case_name和_path_names_to_edges生成mutations和node_edges，然后调用_generate_test_case_from_named_mutations生成迭代数据，最后调用_main_fuzz_loop开始fuzzing

如果没有传入name参数，则通过_generate_mutations_indefinitely生成迭代器然后调用_main_fuzz_loop。

从名字来看不难看出，_generate_test_case_from_named_mutations是生成指定case的迭代器，而_generate_mutations_indefinitely是生成随机的迭代器，在这里我们先不深入探究迭代器的生成，优先走完fuzzing的流程。

```python
def _main_fuzz_loop(self, fuzz_case_iterator):
        """Execute main fuzz logic; takes an iterator of test cases.

        Preconditions: `self.total_mutant_index` and `self.total_num_mutations` are set properly.

        Args:
            fuzz_case_iterator (Iterable): An iterator that walks through fuzz cases and yields MutationContext objects.
                 See _iterate_single_node() for details.

        Returns:
            None
        """
        self.server_init()
```

无论是否指定名字，最终都会来到_main_fuzz_loop函数正式进入fuzzing，_main_fuzz_loop函数接受一个迭代器参数，首先调用server_init()，用来初始化web服务，即我们在 localhost:26000 看到的那个可视化界面。

接下来关注_main_fuzz_loop的主逻辑：

```python
try:
            self._start_target(self.targets[0])

            if self._reuse_target_connection:
                self.targets[0].open()
            self.num_cases_actually_fuzzed = 0
            self.start_time = time.time()
            for mutation_context in fuzz_case_iterator:
                if self.total_mutant_index < self._index_start:
                    continue

                # Check restart interval
                if (
                    self.num_cases_actually_fuzzed
                    and self.restart_interval
                    and self.num_cases_actually_fuzzed % self.restart_interval == 0
                ):
                    self._fuzz_data_logger.open_test_step("restart interval of %d reached" % self.restart_interval)
                    self._restart_target(self.targets[0])

                self._fuzz_current_case(mutation_context)

                self.num_cases_actually_fuzzed += 1

                if self._index_end is not None and self.total_mutant_index >= self._index_end:
                    break

            if self._reuse_target_connection:
                self.targets[0].close()

            if self._keep_web_open and self.web_port is not None:
                self.end_time = time.time()
                print(
                    "\nFuzzing session completed. Keeping webinterface up on localhost:{}".format(self.web_port),
                    "\nPress ENTER to close webinterface",
                )
                input()
        except KeyboardInterrupt:
            # TODO: should wait for the end of the ongoing test case, and stop gracefully netmon and procmon
            self.export_file()
            self._fuzz_data_logger.log_error("SIGINT received ... exiting")
            raise
        except exception.BoofuzzRestartFailedError:
            self._fuzz_data_logger.log_error("Restarting the target failed, exiting.")
            self.export_file()
            raise
        except exception.BoofuzzTargetConnectionFailedError:
            # exception should have already been handled but rethrown in order to escape test run
            pass
        except Exception:
            self._fuzz_data_logger.log_error("Unexpected exception! {0}".format(traceback.format_exc()))
            self.export_file()
            raise
        finally:
            self._fuzz_data_logger.close_test()
```

首先调用了一个_start_target，来简单看看逻辑如何：
```python
def _start_target(self, target):
        started = False
        for monitor in target.monitors:
            if monitor.start_target():
                started = True
                break
        if started:
            for monitor in target.monitors:
                monitor.post_start_target(target=target, fuzz_data_logger=self._fuzz_data_logger, session=self)
```
不难看出，_start_target承担了和监视器开启任务。同样先不去深究监视器，继续往下走，初始化了num_cases_actually_fuzzed和start_time,num_cases_actually_fuzzed用来记录fuzz的次数，start_time用来记录fuzz的开始时间。

而后遍历传入的参数fuzz_case_iterator，检查restart选项

```python
# update the skip variable to pick up fuzzing from last test case.
        self._index_start = data["total_mutant_index"]
        self.session_filename = data["session_filename"]
        self.sleep_time = data["sleep_time"]
        self.restart_sleep_time = data["restart_sleep_time"]
        self.restart_interval = data["restart_interval"]
        self.web_port = data["web_port"]
        self._crash_threshold_node = data["crash_threshold"]
        self.total_num_mutations = data["total_num_mutations"]
        self.total_mutant_index = data["total_mutant_index"]
        self.monitor_results = data["monitor_results"]
        self.is_paused = data["is_paused"]
```
restart_interval是从data中传入的一个参数，表示fuzz到一定次数之后重开target

如果不是第一次fuzz，并且开启了restart interval不为0或none，并且已经fuzz到了restart指定的次数，则记录日志并执行_restart_target重启目标。

否则就执行_fuzz_current_case来fuzz当前case，并让num_cases_actually_fuzzed加一，表示fuzz的次数增加一次。后面则是一系列的异常处理，根据抛出的异常不同打印不同的报错或者进行相应处理。

之前我们看过session的init，里面的restart_interval是默认为0的，所以程序逻辑一般会进入到_fuzz_current_case中，接下来分析一下它的源码长什么样

```python
def _fuzz_current_case(self, mutation_context):
        """
        Fuzzes the current test case. Current test case is controlled by
        fuzz_case_iterator().

        Args:
            mutation_context (MutationContext): Current mutation context.

        """
        target = self.targets[0]

        self._pause_if_pause_flag_is_set()

        test_case_name = self._test_case_name(mutation_context)
        self.current_test_case_name = test_case_name

        self._fuzz_data_logger.open_test_case(
            "{0}: {1}".format(self.total_mutant_index, test_case_name),
            name=test_case_name,
            index=self.total_mutant_index,
            num_mutations=self.total_num_mutations,
            current_index=self.mutant_index,
            current_num_mutations=self.fuzz_node.get_num_mutations(),
        )

        if self.total_num_mutations is not None:
            self._fuzz_data_logger.log_info(
                "Type: {0}. Case {1} of {2} overall.".format(
                    type(self.fuzz_node.mutant).__name__,
                    self.total_mutant_index,
                    self.total_num_mutations,
                )
            )
        else:
            self._fuzz_data_logger.log_info(
                "Type: {0}".format(
                    type(self.fuzz_node.mutant).__name__,
                )
            )

        try:
            self._open_connection_keep_trying(target)

            self._pre_send(target)

            for e in mutation_context.message_path[:-1]:
                prev_node = self.nodes[e.src]
                node = self.nodes[e.dst]
                protocol_session = ProtocolSession(
                    previous_message=prev_node,
                    current_message=node,
                )
                mutation_context.protocol_session = protocol_session
                callback_data = self._callback_current_node(node=node, edge=e, test_case_context=protocol_session)
                self._fuzz_data_logger.open_test_step("Transmit Prep Node '{0}'".format(node.name))
                self.transmit_normal(target, node, e, callback_data=callback_data, mutation_context=mutation_context)

            prev_node = self.nodes[mutation_context.message_path[-1].src]
            node = self.nodes[mutation_context.message_path[-1].dst]
            protocol_session = ProtocolSession(
                previous_message=prev_node,
                current_message=node,
            )
            mutation_context.protocol_session = protocol_session
            callback_data = self._callback_current_node(
                node=self.fuzz_node, edge=mutation_context.message_path[-1], test_case_context=protocol_session
            )
            self._fuzz_data_logger.open_test_step("Fuzzing Node '{0}'".format(self.fuzz_node.name))
            self.transmit_fuzz(
                target,
                self.fuzz_node,
                mutation_context.message_path[-1],
                callback_data=callback_data,
                mutation_context=mutation_context,
            )

            self._check_for_passively_detected_failures(target=target)
            if not self._reuse_target_connection:
                target.close()

            if self.sleep_time > 0:
                self._fuzz_data_logger.open_test_step("Sleep between tests.")
                self._sleep(self.sleep_time)
        except BoofuzzFailure as e:
            self._fuzz_data_logger.log_fail(e.message)
            self._check_for_passively_detected_failures(target=target, failure_already_detected=True)
        finally:
            self._process_failures(target=target)
            self._fuzz_data_logger.close_test_case()
            self.export_file()
```

首先有一个判断是否pause，这里是指在可视化界面有一个pause功能，可以暂停fuzzing，点击pause按钮就会更改_pause_flag，这里通过_pause_if_pause_flag_is_set检测flag，如果表示为pause则停在这里等待重新启动。

然后是一段打印日志的逻辑

然后通过调用_open_connection_keep_trying函数和目标建立连接，如果失败则持续尝试。

通过调用_pre_send执行监视器中注册的回调函数

执行_callback_current_node调用edge的回调函数，而后生成callback_data

执行transmit_fuzz进行实际fuzz数据的收发，最后通过_check_for_passively_detected_failures判断是否产生crash，如果产生crash则进行相应的记录和处理。

最重要的就是这个transmit_fuzz函数，我们最后着重看一下它的实现：
```python
def transmit_fuzz(self, sock, node, edge, callback_data, mutation_context):
        """Render and transmit a fuzzed node, process callbacks accordingly.

        Args:
            sock (Target, optional): Socket-like object on which to transmit node
            node (pgraph.node.node (Node), optional): Request/Node to transmit
            edge (pgraph.edge.edge (pgraph.edge), optional): Edge along the current fuzz path from "node" to next node.
            callback_data (bytes): Data from previous callback.
            mutation_context (MutationContext): Current mutation context.
        """
        if callback_data:
            data = callback_data
        else:
            data = self.fuzz_node.render(mutation_context)

        try:  # send
            self.targets[0].send(data)
            self.last_send = data
        except exception.BoofuzzTargetConnectionReset:
            if self._ignore_connection_issues_when_sending_fuzz_data:
                self._fuzz_data_logger.log_info(constants.ERR_CONN_RESET)
            else:
                raise BoofuzzFailure(message=constants.ERR_CONN_RESET)
        except exception.BoofuzzTargetConnectionAborted as e:
            msg = constants.ERR_CONN_ABORTED.format(socket_errno=e.socket_errno, socket_errmsg=e.socket_errmsg)
            if self._ignore_connection_issues_when_sending_fuzz_data:
                self._fuzz_data_logger.log_info(msg)
            else:
                raise BoofuzzFailure(msg)
        except exception.BoofuzzSSLError as e:
            if self._ignore_connection_ssl_errors:
                self._fuzz_data_logger.log_info(str(e))
            else:
                raise BoofuzzFailure(str(e))

        received = b""
        try:  # recv
            if self._receive_data_after_fuzz:
                received = self.targets[0].recv()
        except exception.BoofuzzTargetConnectionReset:
            if self._check_data_received_each_request:
                raise BoofuzzFailure(message=constants.ERR_CONN_RESET)
            else:
                self._fuzz_data_logger.log_info(constants.ERR_CONN_RESET)
        except exception.BoofuzzTargetConnectionAborted as e:
            msg = constants.ERR_CONN_ABORTED.format(socket_errno=e.socket_errno, socket_errmsg=e.socket_errmsg)
            if self._check_data_received_each_request:
                raise BoofuzzFailure(msg)
            else:
                self._fuzz_data_logger.log_info(msg)
            pass
        except exception.BoofuzzSSLError as e:
            if self._ignore_connection_ssl_errors:
                self._fuzz_data_logger.log_info(str(e))
            else:
                self._fuzz_data_logger.log_fail(str(e))
                raise BoofuzzFailure(str(e))
        self.last_recv = received
```

首先判断是否有callback_data,如果有的话则使用callback_data，如果没有的话则使用变异得来的数据。随后使用自定义的send方法发送数据，并将发送的数据存到last_send中。如果开启了接收数据选项则尝试接收数据，如果接收到了则存到last_recv中。随后跟着的也是很多异常的捕捉和处理。

分析到transmit_fuzz其实已经分析到了最后的实际收发数据的地方。整体的fuzz流程已经走完了。

根据分析过程可以画出如下的流程图来辅助我们理解源码

![0.png](https://www.iotsec-zone.com/images/MdImg/f404c56ef5f63e3723d2db67d1e04a71.png)

但是有一些地方我们为了走完流程，暂时还没有深入进行分析，比如boofuzz是如何产生的变异数据迭代器，我们现在只知道会通过_generate_mutations_indefinitely函数产生这么一个迭代器，然后遍历一遍去进行测试。再比如监视器和重复器到底是干什么用的，状态图部分也就是源码里的pgraph部分是怎么用的等等问题。可以带着这些问题期待源码笔记（三）。
