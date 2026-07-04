/*
 *  Copyright 1999-2004 The Apache Software Foundation
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

import java.util.Iterator;

import org.apache.commons.collections.Unmodifiable;

/** 
 * Decorates an iterator such that it cannot be modified.
 *
 * @since Commons Collections 3.0
 * @version $Revision: 1.5 $ $Date: 2004/02/18 00:59:50 $
 * 
 * @author Stephen Colebourne
 */
public final class UnmodifiableIterator implements Iterator, Unmodifiable {

    /** The iterator being decorated */
    private Iterator iterator;

    //-----------------------------------------------------------------------
    /**
     * Decorates the specified iterator such that it cannot be modified.
     * <p>
     * If the iterator is already unmodifiable it is returned directly.
     *
     * @param iterator  the iterator to decorate
     * @throws IllegalArgumentException if the iterator is null
     */
    public static Iterator decorate(Iterator iterator) {
        if (iterator == null) {
            throw new IllegalArgumentException("Iterator must not be null");
        }
        if (iterator instanceof Unmodifiable) {
            return iterator;
        }
        return new UnmodifiableIterator(iterator);
    }
    
    //-----------------------------------------------------------------------
    /**
     * Constructor.
     *
     * @param iterator  the iterator to decorate
     */
    private UnmodifiableIterator(Iterator iterator) {
        super();
        this.iterator = iterator;
    }

    //-----------------------------------------------------------------------
    public boolean hasNext() {
        return iterator.hasNext();
    }

    public Object next() {
        return iterator.next();
    }

    public void remove() {
        throw new UnsupportedOperationException("remove() is not supported");
    }

}
