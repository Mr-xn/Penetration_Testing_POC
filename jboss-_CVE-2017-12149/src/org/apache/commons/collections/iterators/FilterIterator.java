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
import java.util.NoSuchElementException;

import org.apache.commons.collections.Predicate;

/** 
 * Decorates an iterator such that only elements matching a predicate filter
 * are returned.
 *
 * @since Commons Collections 1.0
 * @version $Revision: 1.8 $ $Date: 2004/02/18 00:59:50 $
 * 
 * @author James Strachan
 * @author Jan Sorensen
 * @author Ralph Wagner
 * @author Stephen Colebourne
 */
public class FilterIterator implements Iterator {

    /** The iterator being used */
    private Iterator iterator;
    /** The predicate being used */
    private Predicate predicate;
    /** The next object in the iteration */
    private Object nextObject;
    /** Whether the next object has been calculated yet */
    private boolean nextObjectSet = false;

    //-----------------------------------------------------------------------
    /**
     * Constructs a new <code>FilterIterator</code> that will not function
     * until {@link #setIterator(Iterator) setIterator} is invoked.
     */
    public FilterIterator() {
        super();
    }

    /**
     * Constructs a new <code>FilterIterator</code> that will not function
     * until {@link #setPredicate(Predicate) setPredicate} is invoked.
     *
     * @param iterator  the iterator to use
     */
    public FilterIterator(Iterator iterator) {
        super();
        this.iterator = iterator;
    }

    /**
     * Constructs a new <code>FilterIterator</code> that will use the
     * given iterator and predicate.
     *
     * @param iterator  the iterator to use
     * @param predicate  the predicate to use
     */
    public FilterIterator(Iterator iterator, Predicate predicate) {
        super();
        this.iterator = iterator;
        this.predicate = predicate;
    }

    //-----------------------------------------------------------------------
    /** 
     * Returns true if the underlying iterator contains an object that 
     * matches the predicate.
     *
     * @return true if there is another object that matches the predicate 
     */
    public boolean hasNext() {
        if (nextObjectSet) {
            return true;
        } else {
            return setNextObject();
        }
    }

    /** 
     * Returns the next object that matches the predicate.
     * 
     * @return the next object which matches the given predicate
     * @throws NoSuchElementException if there are no more elements that
     *  match the predicate 
     */
    public Object next() {
        if (!nextObjectSet) {
            if (!setNextObject()) {
                throw new NoSuchElementException();
            }
        }
        nextObjectSet = false;
        return nextObject;
    }

    /**
     * Removes from the underlying collection of the base iterator the last
     * element returned by this iterator.
     * This method can only be called
     * if <code>next()</code> was called, but not after
     * <code>hasNext()</code>, because the <code>hasNext()</code> call
     * changes the base iterator.
     * 
     * @throws IllegalStateException if <code>hasNext()</code> has already
     *  been called.
     */
    public void remove() {
        if (nextObjectSet) {
            throw new IllegalStateException("remove() cannot be called");
        }
        iterator.remove();
    }

    //-----------------------------------------------------------------------
    /** 
     * Gets the iterator this iterator is using.
     * 
     * @return the iterator.
     */
    public Iterator getIterator() {
        return iterator;
    }

    /** 
     * Sets the iterator for this iterator to use.
     * If iteration has started, this effectively resets the iterator.
     * 
     * @param iterator  the iterator to use
     */
    public void setIterator(Iterator iterator) {
        this.iterator = iterator;
    }

    //-----------------------------------------------------------------------
    /** 
     * Gets the predicate this iterator is using.
     * 
     * @return the predicate.
     */
    public Predicate getPredicate() {
        return predicate;
    }

    /** 
     * Sets the predicate this the iterator to use.
     * 
     * @param predicate  the transformer to use
     */
    public void setPredicate(Predicate predicate) {
        this.predicate = predicate;
    }

    //-----------------------------------------------------------------------
    /**
     * Set nextObject to the next object. If there are no more 
     * objects then return false. Otherwise, return true.
     */
    private boolean setNextObject() {
        while (iterator.hasNext()) {
            Object object = iterator.next();
            if (predicate.evaluate(object)) {
                nextObject = object;
                nextObjectSet = true;
                return true;
            }
        }
        return false;
    }
}
