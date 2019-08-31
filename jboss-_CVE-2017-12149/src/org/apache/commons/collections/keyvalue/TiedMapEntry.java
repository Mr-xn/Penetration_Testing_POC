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
package org.apache.commons.collections.keyvalue;

import java.io.Serializable;
import java.util.Map;

import org.apache.commons.collections.KeyValue;

/**
 * A Map Entry tied to a map underneath.
 * <p>
 * This can be used to enable a map entry to make changes on the underlying
 * map, however this will probably mess up any iterators.
 *
 * @since Commons Collections 3.0
 * @version $Revision: 1.5 $ $Date: 2004/04/09 14:35:10 $
 * 
 * @author Stephen Colebourne
 */
public class TiedMapEntry implements Map.Entry, KeyValue, Serializable {

    /** Serialization version */    
    private static final long serialVersionUID = -8453869361373831205L;

    /** The map underlying the entry/iterator */    
    private final Map map;
    /** The key */
    private final Object key;
    
    /**
     * Constructs a new entry with the given Map and key.
     *
     * @param map  the map
     * @param key  the key
     */
    public TiedMapEntry(Map map, Object key) {
        super();
        this.map = map;
        this.key = key;
    }

    // Map.Entry interface
    //-------------------------------------------------------------------------
    /**
     * Gets the key of this entry
     * 
     * @return the key
     */
    public Object getKey() {
        return key;
    }

    /**
     * Gets the value of this entry direct from the map.
     * 
     * @return the value
     */
    public Object getValue() {
        return map.get(key);
    }

    /**
     * Sets the value associated with the key direct onto the map.
     * 
     * @param value  the new value
     * @return the old value
     * @throws IllegalArgumentException if the value is set to this map entry
     */
    public Object setValue(Object value) {
        if (value == this) {
            throw new IllegalArgumentException("Cannot set value to this map entry");
        }
        return map.put(key, value);
    }

    /**
     * Compares this Map Entry with another Map Entry.
     * <p>
     * Implemented per API documentation of {@link java.util.Map.Entry#equals(Object)}
     * 
     * @param obj  the object to compare to
     * @return true if equal key and value
     */
    public boolean equals(Object obj) {
        if (obj == this) {
            return true;
        }
        if (obj instanceof Map.Entry == false) {
            return false;
        }
        Map.Entry other = (Map.Entry) obj;
        Object value = getValue();
        return
            (key == null ? other.getKey() == null : key.equals(other.getKey())) &&
            (value == null ? other.getValue() == null : value.equals(other.getValue()));
    }
     
    /**
     * Gets a hashCode compatible with the equals method.
     * <p>
     * Implemented per API documentation of {@link java.util.Map.Entry#hashCode()}
     * 
     * @return a suitable hash code
     */
    public int hashCode() {
        Object value = getValue();
        return (getKey() == null ? 0 : getKey().hashCode()) ^
               (value == null ? 0 : value.hashCode()); 
    }
    
    /**
     * Gets a string version of the entry.
     * 
     * @return entry as a string
     */
    public String toString() {
        return getKey() + "=" + getValue();
    }

}
