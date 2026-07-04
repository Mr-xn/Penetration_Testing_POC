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

import org.apache.commons.collections.KeyValue;

/**
 * Provides a base decorator that allows additional functionality to be added
 * to a Map Entry.
 *
 * @since Commons Collections 3.0
 * @version $Revision: 1.4 $ $Date: 2004/02/18 01:00:08 $
 * 
 * @author Stephen Colebourne
 */
public abstract class AbstractMapEntryDecorator implements Map.Entry, KeyValue {
    
    /** The <code>Map.Entry</code> to decorate */
    protected final Map.Entry entry;

    /**
     * Constructor that wraps (not copies).
     *
     * @param entry  the <code>Map.Entry</code> to decorate, must not be null
     * @throws IllegalArgumentException if the collection is null
     */
    public AbstractMapEntryDecorator(Map.Entry entry) {
        if (entry == null) {
            throw new IllegalArgumentException("Map Entry must not be null");
        }
        this.entry = entry;
    }

    /**
     * Gets the map being decorated.
     * 
     * @return the decorated map
     */
    protected Map.Entry getMapEntry() {
        return entry;
    }

    //-----------------------------------------------------------------------
    public Object getKey() {
        return entry.getKey();
    }

    public Object getValue() {
        return entry.getValue();
    }

    public Object setValue(Object object) {
        return entry.setValue(object);
    }
   
    public boolean equals(Object object) {
        if (object == this) {
            return true;
        }
        return entry.equals(object);
    }

    public int hashCode() {
        return entry.hashCode();
    }

    public String toString() {
        return entry.toString();
    }

}
