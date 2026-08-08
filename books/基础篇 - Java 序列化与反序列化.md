# 基础篇 - Java 序列化与反序列化
> 2024-05-10
> 来源：https://changeyourway.github.io/2024/05/10/Java%20%E5%AE%89%E5%85%A8/%E5%9F%BA%E7%A1%80%E7%AF%87-Java%E5%BA%8F%E5%88%97%E5%8C%96%E4%B8%8E%E5%8F%8D%E5%BA%8F%E5%88%97%E5%8C%96/

Java 序列化是指把 Java 对象转换为字节序列的过程，而 Java 反序列化是指把字节序列恢复为 Java 对象的过程。本文详细讲解了 Java 序列化与反序列化的实现。

## Java 序列化与反序列化

### 概述

Java 序列化是指把 Java 对象转换为字节序列的过程，而 Java 反序列化是指把字节序列恢复为 Java 对象的过程。

### 序列化与反序列化实现

##### 条件

只有实现了 `Serializable` 或者 `Externalizable` 接口的类的对象才能被序列化为字节序列。（不是则会抛出异常）

###### Serializable 接口

`Serializable` 接口是 Java 提供的序列化接口，它是一个空接口：

```
public interface Serializable {
}
```

`Serializable` 用来标识当前类可以被 `ObjectOutputStream` 序列化，以及被 `ObjectInputStream` 反序列化。

###### Externalizable 接口

`Externalizable` 接口是一个更高级别的序列化机制，它允许类对序列化和反序列化过程进行更多的控制和自定义。

实现了 `Externalizable` 接口的类可以被序列化，但是它与实现 `Serializable` 接口的类有所不同，`Externalizable` 接口的序列化和反序列化方法对对象的状态完全负责，包括对象的所有成员变量。因此，在 `writeExternal` 和 `readExternal` 方法中，需要手动指定对象的所有成员变量的序列化和反序列化过程。

-   类必须显式实现 `Externalizable` 接口。
    
-   类必须实现 `writeExternal` 和 `readExternal` 方法来手动指定对象的序列化和反序列化过程。这些方法负责将对象的状态写入和读取到指定的数据流中。
    
-   类必须提供一个公共的无参数构造函数，因为反序列化过程需要调用该构造函数来创建对象实例。
    
    以下是代码示例：
    
    ```
    import java.io.*;
    
    public class MyClass implements Externalizable {
      private int id;
      private String name;
    
      // 必须提供默认的构造函数
      public MyClass() {}
    
      public MyClass(int id, String name) {
          this.id = id;
          this.name = name;
      }
    
      // 实现序列化的方法
      @Override
      public void writeExternal(ObjectOutput out) throws IOException {
          out.writeInt(id);
          out.writeUTF(name);
      }
    
      // 实现反序列化的方法
      @Override
      public void readExternal(ObjectInput in) throws IOException, ClassNotFoundException {
          id = in.readInt();
          name = in.readUTF();
      }
    
    }
    ```
    

###### 其他条件

除此之外，反序列化还有一些条件：

1.  **对象的所有成员都可序列化**：如果一个类实现了 `Serializable` 接口，但其成员中有某些成员变量不可序列化，则序列化操作会失败。
2.  **静态成员变量不参与序列化**：静态成员变量属于类级别的数据，不包含在序列化的过程中。
3.  **transient 关键字**：如果某个成员变量被声明为 `transient`，则在序列化过程中会被忽略，不会被持久化。
4.  **序列化版本号 serialVersionUID**：序列化版本号不一致反序列化会失败。建议显式声明一个名为 `serialVersionUID` 的静态变量，用于控制序列化的版本。若不声明，Java 会根据类的结构自动生成一个版本号，若类的结构发生变化，则版本号不同，无法反序列化。

##### 序列化对象

要将对象序列化成字节流，可以使用 `ObjectOutputStream` 类。通过 `ObjectOutputStream` 的 `writeObject()` 方法将对象写入输出流。

代码示例：

```
import java.io.FileOutputStream;
import java.io.ObjectOutputStream;

public class SerializationExample {
    public static void main(String[] args) {
        try {
            MyClass obj = new MyClass();
            FileOutputStream fileOut = new FileOutputStream("object.ser");
            ObjectOutputStream out = new ObjectOutputStream(fileOut);
            out.writeObject(obj);
            out.close();
            fileOut.close();
            System.out.println("Object has been serialized");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

##### 反序列化字节流

要从字节流中反序列化对象，可以使用 `ObjectInputStream` 类。通过 `ObjectInputStream` 的 `readObject()` 方法读取输入流中的对象。

代码示例：

```
import java.io.FileInputStream;
import java.io.ObjectInputStream;

public class DeserializationExample {
    public static void main(String[] args) {
        try {
            FileInputStream fileIn = new FileInputStream("object.ser");
            ObjectInputStream in = new ObjectInputStream(fileIn);
            MyClass obj = (MyClass) in.readObject();
            in.close();
            fileIn.close();
            System.out.println("Object has been deserialized");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

##### 使用 ObjectOutputStream 与 ObjectInputStream 的注意事项

在上面的代码中，使用 `ObjectOutputStream`（ `ObjectInputStream` ）之前，先使用了 `FileOutputStream`（`FileInputStream` ）来处理数据。

实际上，`ObjectOutputStream` 需要一个输出流作为参数，因此在使用 `ObjectOutputStream` 之前，先使用 `FileOutputStream` 打开文件并创建一个文件输出流对象，以便将对象序列化后的数据写入文件。

同理，`ObjectInputStream` 是基于输入流的，它需要一个输入流作为参数来读取对象的序列化数据。而 `FileInputStream` 是一种输入流，用于从文件中读取字节流数据。

此外，重要的一点是：

ObjectOutputStream 中进行序列化操作的时候，会判断被序列化的对象是否自己重写了 writeObject 方法，如果重写了，就会调用被序列化对象自己的 writeObject 方法，如果没有重写，才会调用默认的序列化方法。

同理 ObjectInputStream 中进行序列化操作的时候，会判断被序列化的对象是否自己重写了 readObject方法，如果重写了，就会调用被序列化对象自己的 readObject方法，如果没有重写，才会调用默认的序列化方法。

##### 常见的输入输出流

除了 `FileInputStream`（ `FileOutputStream`）之外，根据条件的不同，还可以使用其他的输入输出流来处理数据。

以下是一些常见的输入输出流以及它们的使用条件：

1.  **BufferedInputStream**（**BufferedOutputStream**）：
    -   使用条件：当需要对读取或写入的数据进行缓冲以提高性能时，特别是对大文件或网络数据流的读取或写入。
2.  **ByteArrayInputStream**（**ByteArrayOutputStream**）：
    -   使用条件：当需要从字节数组中读取数据，或将数据写入到字节数组中时。
3.  **ObjectInputStream**（**ObjectOutputStream**）：
    -   使用条件：当需要将输入流中的数据反序列化为对象，或将对象序列化后的数据写入到输出流时。
4.  **PipedInputStream**（**PipedOutputStream**）：
    -   使用条件：当需要通过管道与另一个线程进行数据交换时，可用于线程间通信。
5.  **DataInputStream**（**DataOutputStream**）：
    -   使用条件：当需要从输入流中以 Java 基本数据类型的格式读取数据，或以 Java 基本数据类型的格式将数据写入输出流时。
6.  **FileInputStream**（**FileOutputStream**）：
    -   使用条件：当需要从文件中读取字节数据，或将数据写入文件时。
7.  **其他自定义的 InputStream**（**OutputStream**）：
    -   使用条件：如果有特定的需求，可以自定义实现 `InputStream`（`OutputStream`）类的子类，来满足自己的需求，比如从特定硬件设备中读取数据等。

##### 序列化版本号 serialVersionUID

Java 的序列化机制是通过判断运行时类的 serialVersionUID 来验证版本一致性的，在进行反序列化时，JVM 会把传进来的字节流中的 serialVersionUID 与本地实体类中的 serialVersionUID 进行比较，如果相同则认为是一致的，便可以进行反序列化，否则就会报序列化版本不一致的异常。

如果没有显示指定 serialVersionUID ，Java 会根据类的结构自动生成一个，这种情况下，只有同一次编译生成的 class 才会生成相同的 serialVersionUID 。

有时候由于 serialVersionUID 发生改变，导致反序列化不能成功，为了不出现这类的问题，可以在要序列化的类中显式的声明一个名为 “ serialVersionUID ” 、类型为 long 的变量，并指定其值：

```
private static final long serialVersionUID = 1L;
```

这样就解决了兼容性问题。
