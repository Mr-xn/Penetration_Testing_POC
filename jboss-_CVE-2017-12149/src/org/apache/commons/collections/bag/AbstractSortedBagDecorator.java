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
package org.apache.commons.collections.bag;

import java.util.Comparator;

import org.apache.commons.collections.SortedBag;

/**
 * Decorates another <code>SortedBag</code> to provide additional behaviour.
 * <p>
 * Methods are forwarded directly to the decorated bag.
 *
 * @since Commons Collections 3.0
 * @version $Revision: 1.5 $ $Date: 2004/06/02 21:53:02 $
 * 
 * @author Stephen Colebourne
 */
public abstract class AbstractSortedBagDecorator
        extends AbstractBagDecorator implements SortedBag {

    /**
     * Constructor only used in deserialization, do not use otherwise.
     * @since Commons Collections 3.1
     */
    protected AbstractSortedBagDecorator() {
        super();
    }

    /**
     * Constructor that wraps (not copies).
     * 
     * @param bag  the bag to decorate, must not be null
     * @throws IllegalArgumentException if list is null
     */
    protected AbstractSortedBagDecorator(SortedBag bag) {
        super(bag);
    }

    /**
     * Gets the bag being decorated.
     * 
     * @return the decorated bag
     */
    protected SortedBag getSortedBag() {
        return (SortedBag) getCollection();
    }

    //-----------------------------------------------------------------------
    public Object first() {
        return getSortedBag().first();
    }

    public Object last() {
        return getSortedBag().last();
    }

    public Comparator comparator() {
        return getSortedBag().comparator();
    }

}
