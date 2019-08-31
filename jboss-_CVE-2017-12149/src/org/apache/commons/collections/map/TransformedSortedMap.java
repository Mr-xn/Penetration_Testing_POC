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

import java.util.Comparator;
import java.util.SortedMap;

import org.apache.commons.collections.Transformer;

/**
 * Decorates another <code>SortedMap </code> to transform objects that are added.
 * <p>
 * The Map put methods and Map.Entry setValue method are affected by this class.
 * Thus objects must be removed or searched for using their transformed form.
 * For example, if the transformation converts Strings to Integers, you must
 * use the Integer form to remove objects.
 * <p>
 * This class is Serializable from Commons Collections 3.1.
 *
 * @since Commons Collections 3.0
 * @version $Revision: 1.6 $ $Date: 2004/04/09 10:36:01 $
 * 
 * @author Stephen Colebourne
 */
public class TransformedSortedMap
        extends TransformedMap
        implements SortedMap {

    /** Serialization version */
    private static final long serialVersionUID = -8751771676410385778L;
    
    /**
     * Factory method to create a transforming sorted map.
     * <p>
     * If there are any elements already in the map being decorated, they
     * are NOT transformed.
     * 
     * @param map  the map to decorate, must not be null
     * @param keyTransformer  the predicate to validate the keys, null means no transformation
     * @param valueTransformer  the predicate to validate to values, null means no transformation
     * @throws IllegalArgumentException if the map is null
     */
    public static SortedMap decorate(SortedMap map, Transformer keyTransformer, Transformer valueTransformer) {
        return new TransformedSortedMap(map, keyTransformer, valueTransformer);
    }

    //-----------------------------------------------------------------------
    /**
     * Constructor that wraps (not copies).
     * <p>
     * If there are any elements already in the collection being decorated, they
     * are NOT transformed.</p>
     * 
     * @param map  the map to decorate, must not be null
     * @param keyTransformer  the predicate to validate the keys, null means no transformation
     * @param valueTransformer  the predicate to validate to values, null means no transformation
     * @throws IllegalArgumentException if the map is null
     */
    protected TransformedSortedMap(SortedMap map, Transformer keyTransformer, Transformer valueTransformer) {
        super(map, keyTransformer, valueTransformer);
    }

    //-----------------------------------------------------------------------
    /**
     * Gets the map being decorated.
     * 
     * @return the decorated map
     */
    protected SortedMap getSortedMap() {
        return (SortedMap) map;
    }

    //-----------------------------------------------------------------------
    public Object firstKey() {
        return getSortedMap().firstKey();
    }

    public Object lastKey() {
        return getSortedMap().lastKey();
    }

    public Comparator comparator() {
        return getSortedMap().comparator();
    }

    public SortedMap subMap(Object fromKey, Object toKey) {
        SortedMap map = getSortedMap().subMap(fromKey, toKey);
        return new TransformedSortedMap(map, keyTransformer, valueTransformer);
    }

    public SortedMap headMap(Object toKey) {
        SortedMap map = getSortedMap().headMap(toKey);
        return new TransformedSortedMap(map, keyTransformer, valueTransformer);
    }

    public SortedMap tailMap(Object fromKey) {
        SortedMap map = getSortedMap().tailMap(fromKey);
        return new TransformedSortedMap(map, keyTransformer, valueTransformer);
    }

}
