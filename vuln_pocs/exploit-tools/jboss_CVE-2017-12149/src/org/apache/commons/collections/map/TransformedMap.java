/*
 *  Copyright 2003-2004 The Apache Software Foundation
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package org.apache.commons.collections.map;

import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.util.Iterator;
import java.util.Map;

import org.apache.commons.collections.Transformer;

/**
 * Decorates another <code>Map</code> to transform objects that are added.
 * <p>
 * The Map put methods and Map.Entry setValue method are affected by this class.
 * Thus objects must be removed or searched for using their transformed form.
 * For example, if the transformation converts Strings to Integers, you must
 * use the Integer form to remove objects.
 * <p>
 * This class is Serializable from Commons Collections 3.1.
 *
 * @since Commons Collections 3.0
 * @version $Revision: 1.11 $ $Date: 2004/06/07 22:14:42 $
 * 
 * @author Stephen Colebourne
 */
public class TransformedMap
        extends AbstractInputCheckedMapDecorator
        implements Serializable {

    /** Serialization version */
    private static final long serialVersionUID = 7023152376788900464L;

    /** The transformer to use for the key */
    protected final Transformer keyTransformer;
    /** The transformer to use for the value */
    protected final Transformer valueTransformer;

    /**
     * Factory method to create a transforming map.
     * <p>
     * If there are any elements already in the map being decorated, they
     * are NOT transformed.
     * 
     * @param map  the map to decorate, must not be null
     * @param keyTransformer  the transformer to use for key conversion, null means no conversion
     * @param valueTransformer  the transformer to use for value conversion, null means no conversion
     * @throws IllegalArgumentException if map is null
     */
    public static Map decorate(Map map, Transformer keyTransformer, Transformer valueTransformer) {
        return new TransformedMap(map, keyTransformer, valueTransformer);
    }

    //-----------------------------------------------------------------------
    /**
     * Constructor that wraps (not copies).
     * <p>
     * If there are any elements already in the collection being decorated, they
     * are NOT transformed.
     * 
     * @param map  the map to decorate, must not be null
     * @param keyTransformer  the transformer to use for key conversion, null means no conversion
     * @param valueTransformer  the transformer to use for value conversion, null means no conversion
     * @throws IllegalArgumentException if map is null
     */
    protected TransformedMap(Map map, Transformer keyTransformer, Transformer valueTransformer) {
        super(map);
        this.keyTransformer = keyTransformer;
        this.valueTransformer = valueTransformer;
    }

    //-----------------------------------------------------------------------
    /**
     * Write the map out using a custom routine.
     * 
     * @param out  the output stream
     * @throws IOException
     * @since Commons Collections 3.1
     */
    private void writeObject(ObjectOutputStream out) throws IOException {
        out.defaultWriteObject();
        out.writeObject(map);
    }

    /**
     * Read the map in using a custom routine.
     * 
     * @param in  the input stream
     * @throws IOException
     * @throws ClassNotFoundException
     * @since Commons Collections 3.1
     */
    private void readObject(ObjectInputStream in) throws IOException, ClassNotFoundException {
        in.defaultReadObject();
        map = (Map) in.readObject();
    }

    //-----------------------------------------------------------------------
    /**
     * Transforms a key.
     * <p>
     * The transformer itself may throw an exception if necessary.
     * 
     * @param object  the object to transform
     * @throws the transformed object
     */
    protected Object transformKey(Object object) {
        if (keyTransformer == null) {
            return object;
        }
        return keyTransformer.transform(object);
    }

    /**
     * Transforms a value.
     * <p>
     * The transformer itself may throw an exception if necessary.
     * 
     * @param object  the object to transform
     * @throws the transformed object
     */
    protected Object transformValue(Object object) {
        if (valueTransformer == null) {
            return object;
        }
        return valueTransformer.transform(object);
    }

    /**
     * Transforms a map.
     * <p>
     * The transformer itself may throw an exception if necessary.
     * 
     * @param map  the map to transform
     * @throws the transformed object
     */
    protected Map transformMap(Map map) {
        Map result = new LinkedMap(map.size());
        for (Iterator it = map.entrySet().iterator(); it.hasNext(); ) {
            Map.Entry entry = (Map.Entry) it.next();
            result.put(transformKey(entry.getKey()), transformValue(entry.getValue()));
        }
        return result;
    }

    /**
     * Override to transform the value when using <code>setValue</code>.
     * 
     * @param value  the value to transform
     * @return the transformed value
     * @since Commons Collections 3.1
     */
    protected Object checkSetValue(Object value) {
        return valueTransformer.transform(value);
    }

    /**
     * Override to only return true when there is a value transformer.
     * 
     * @return true if a value transformer is in use
     * @since Commons Collections 3.1
     */
    protected boolean isSetValueChecking() {
        return (valueTransformer != null);
    }

    //-----------------------------------------------------------------------
    public Object put(Object key, Object value) {
        key = transformKey(key);
        value = transformValue(value);
        return getMap().put(key, value);
    }

    public void putAll(Map mapToCopy) {
        mapToCopy = transformMap(mapToCopy);
        getMap().putAll(mapToCopy);
    }

}
