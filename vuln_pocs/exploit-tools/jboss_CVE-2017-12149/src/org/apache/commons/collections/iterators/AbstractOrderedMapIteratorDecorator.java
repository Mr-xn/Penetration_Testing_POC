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
package org.apache.commons.collections.iterators;

import org.apache.commons.collections.OrderedMapIterator;

/**
 * Provides basic behaviour for decorating an ordered map iterator with extra functionality.
 * <p>
 * All methods are forwarded to the decorated map iterator.
 *
 * @since Commons Collections 3.0
 * @version $Revision: 1.4 $ $Date: 2004/02/18 00:59:50 $
 * 
 * @author Stephen Colebourne
 */
public class AbstractOrderedMapIteratorDecorator implements OrderedMapIterator {

    /** The iterator being decorated */
    protected final OrderedMapIterator iterator;

    //-----------------------------------------------------------------------
    /**
     * Constructor that decorates the specified iterator.
     *
     * @param iterator  the iterator to decorate, must not be null
     * @throws IllegalArgumentException if the collection is null
     */
    public AbstractOrderedMapIteratorDecorator(OrderedMapIterator iterator) {
        super();
        if (iterator == null) {
            throw new IllegalArgumentException("OrderedMapIterator must not be null");
        }
        this.iterator = iterator;
    }

    /**
     * Gets the iterator being decorated.
     * 
     * @return the decorated iterator
     */
    protected OrderedMapIterator getOrderedMapIterator() {
        return iterator;
    }

    //-----------------------------------------------------------------------
    public boolean hasNext() {
        return iterator.hasNext();
    }

    public Object next() {
        return iterator.next();
    }

    public boolean hasPrevious() {
        return iterator.hasPrevious();
    }

    public Object previous() {
        return iterator.previous();
    }

    public void remove() {
        iterator.remove();
    }
    
    public Object getKey() {
        return iterator.getKey();
    }

    public Object getValue() {
        return iterator.getValue();
    }

    public Object setValue(Object obj) {
        return iterator.setValue(obj);
    }

}
