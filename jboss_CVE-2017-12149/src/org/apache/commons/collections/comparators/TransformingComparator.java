/*
 *  Copyright 2001-2004 The Apache Software Foundation
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
package org.apache.commons.collections.comparators;

import java.util.Comparator;

import org.apache.commons.collections.Transformer;

/**
 * Decorates another Comparator with transformation behavior. That is, the
 * return value from the transform operation will be passed to the decorated
 * {@link Comparator#compare(Object,Object) compare} method.
 * 
 * @since Commons Collections 2.0 (?)
 * @version $Revision$ $Date$
 * 
 * @see org.apache.commons.collections.Transformer
 * @see org.apache.commons.collections.comparators.ComparableComparator
 */
public class TransformingComparator implements Comparator {
    
    /** The decorated comparator. */
    protected Comparator decorated;
    /** The transformer being used. */    
    protected Transformer transformer;

    //-----------------------------------------------------------------------
    /**
     * Constructs an instance with the given Transformer and a 
     * {@link ComparableComparator ComparableComparator}.
     * 
     * @param transformer what will transform the arguments to <code>compare</code>
     */
    public TransformingComparator(Transformer transformer) {
        this(transformer, new ComparableComparator());
    }

    /**
     * Constructs an instance with the given Transformer and Comparator.
     * 
     * @param transformer  what will transform the arguments to <code>compare</code>
     * @param decorated  the decorated Comparator
     */
    public TransformingComparator(Transformer transformer, Comparator decorated) {
        this.decorated = decorated;
        this.transformer = transformer;
    }

    //-----------------------------------------------------------------------
    /**
     * Returns the result of comparing the values from the transform operation.
     * 
     * @param obj1  the first object to transform then compare
     * @param obj2  the second object to transform then compare
     * @return negative if obj1 is less, positive if greater, zero if equal
     */
    public int compare(Object obj1, Object obj2) {
        Object value1 = this.transformer.transform(obj1);
        Object value2 = this.transformer.transform(obj2);
        return this.decorated.compare(value1, value2);
    }

}

