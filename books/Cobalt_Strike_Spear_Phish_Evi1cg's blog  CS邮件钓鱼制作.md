Cobalt Strike Spear Phish | Evi1cg's blog  

![img](./img/01.jpg)  

## 0x00 简介  

关于 Spear phish 和发件人伪造的工具有很多个，比如 [gophish](https://getgophish.com/)、 [SimpleEmailSpoofer](https://github.com/lunarca/SimpleEmailSpoofer)、命令行工具 swaks 等，每个工具都有其特点，当然 Cobalt Strike 也有此功能。官方介绍[戳我](https://cobaltstrike.com/help-spear-phish)。今天主要来介绍一下 CS 里面的此功能怎么使用。  

## 0x01 CS Spear Phish  

CS 的 Spear Phish 位置在：  

![img](./img/02.jpg)  

一张图说明功能：  

![img](./img/03.jpg)  

使用此功能的前提是需要有一个 smtp 服务器来供我们来转发邮件，当然可以使用公共 smtp 服务，另外也可以参考[《Something about email spoofing》](https://evi1cg.github.io/archives/Email_spoofing.html) 中提到的方法来搭建。  
这里的使用很简单，首先构造目标列表，使用：  

中间的分隔符为 [tab], 可以不添加 name  

添加好以后就是这个样子：  

![img](./img/04.jpg)  

下面，要配置发件模板，这里配置很简单，只需要复制一份原始邮件即可，比如一份密码重置邮件：  

![img](./img/05.jpg)  

选择显示原始邮件，并将其内容保存。  

在这里如果要伪造发件人，需要修改`From:`  

![img](./img/06.jpg)   

否则就不需要做什么别的修改。之后，配置对应的`Mail server`，就可以进行发送邮件了，这里需要注意一点, 为了绕过 SPF 的检查，`Bunce to`需设置为与`Mail server`同域，如`Mail server`为 `mail.evi1cg.me`,`Bunce to`可设置为 [`admin@evi1cg.me](mailto:`admin@evi1cg.me)`。


之后点击`Send`则可发送邮件，收到的邮件与模板一致。  

![img](./img/07.jpg)  

另外查看 SRF 为`PASS`状态：  



![img](./img/08.jpg)  

另外，CS 也有发送附件的功能，但是原版本的 CS 发送附件有一个 Bug，即如果附件为中文名称，则会在最后的邮件中显示乱码附件：  

![img](./img/09.jpg)  

所以在这里我们需要对 CS 动刀了，经过调试，成功定位到`mail\Eater.java`，需要对此类中的`createAttachment`方法进行修改：  

```
private BodyPart createAttachment(String name) throws IOException {
   File file = new File(name);
   String namez = file.getName();
   String filename = new String(namez.getBytes("utf-8"),"ISO8859-1");
   Body body = (new StorageBodyFactory()).binaryBody((InputStream)(new FileInputStream(name)));
   Map temp = new HashMap();
   temp.put("name", filename);
   BodyPart bodyPart = new BodyPart();
   bodyPart.setBody(body, "application/octet-stream", temp);
   bodyPart.setContentTransferEncoding("base64");
   bodyPart.setContentDisposition("attachment");
   bodyPart.setFilename(filename);
   return bodyPart;
}
```

这样就可以解决附件乱码问题了:  

![img](./img/10.jpg)  

## 0x02 Web clone  

另外在这里还有一个与 Web Clone 结合的地方，首先，我们先 Clone 一个需登录的网站，如网易邮箱：  

![img](./img/11.jpg)  

这里可以选择开启键盘记录功能。  

开启 Clone：  

![img](./img/12.jpg)  

设置 spear phish:  

![img](./img/13.jpg)  

Embed URL 选择刚刚克隆的 url，发送邮件，此时用户点击重置按钮，则会跳转到 Clone 的站点：  

![img](./img/14.gif)  

此时，用户输入会被记录：  

![img](./img/15.gif)  

emmm. 大概就介绍这么多吧。  

原文地址：<https://evi1cg.me/archives/spear_phish.html>

