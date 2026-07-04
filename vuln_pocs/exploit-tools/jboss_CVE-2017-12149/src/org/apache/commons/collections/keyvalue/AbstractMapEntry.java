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

import java.util.Map;

/**
 * Abstract Pair class to assist with creating correct Map Entry implementations.
 *
 * @since Commons Collections 3.0
 * @version $Revision: 1.4 $ $Date: 2004/02/18 01:00:08 $
 * 
 * @author James Strachan
 * @author Michael A. Smith
 * @author Neil O'Toole
 * @author Stephen Colebourne
 */
public abstract class AbstractMapEntry extends AbstractKeyValue implements Map.Entry {
    
    /**
     * Constructs a new entry with the given key and given value.
     *
     * @param key  the key for the entry, may be null
     * @param value  the value for the entry, may be null
     */
    protected AbstractMapEntry(Object key, Object value) {
        super(key, value);
    }

    // Map.Entry interface
    //-------------------------------------------------------------------------
    /** 
     * Sets the value stored in this Map Entry.
     * <p>
     * This Map Entry is not connected to a Map, so only the local data is changed.
     *
     * @param value  the new value
     * @return the previous value
     */
    public Object setValue(Object value) {
        Object answer = this.value;
        this.value = value;
        return answer;
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
        return
            (getKey() == null ? other.getKey() == null : getKey().equals(other.getKey())) &&
            (getValue() == null ? other.getValue() == null : getValue().equals(other.getValue()));
    }
     
    /**
     * Gets a hashCode compatible with the equals method.
     * <p>
     * Implemented per API documentation of {@link java.util.Map.Entry#hashCode()}
     * 
     * @return a suitable hash code
     */
    public int hashCode() {
        return (getKey() == null ? 0 : getKey().hashCode()) ^
               (getValue() == null ? 0 : getValue().hashCode()); 
    }

}
