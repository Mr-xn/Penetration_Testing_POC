/*
 *  Copyright 2004 The Apache Software Foundation
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

import org.apache.commons.collections.ResettableIterator;

/** 
 * Provides an implementation of an empty iterator.
 * <p>
 * This class provides an implementation of an empty iterator.
 * This class provides for binary compatability between Commons Collections
 * 2.1.1 and 3.1 due to issues with <code>IteratorUtils</code>.
 *
 * @since Commons Collections 2.1.1 and 3.1
 * @version $Revision: 1.1 $ $Date: 2004/05/22 09:46:39 $
 * 
 * @author Stephen Colebourne
 */
public class EmptyIterator extends AbstractEmptyIterator implements ResettableIterator {

    /**
     * Singleton instance of the iterator.
     * @since Commons Collections 3.1
     */
    public static final ResettableIterator RESETTABLE_INSTANCE = new EmptyIterator();
    /**
     * Singleton instance of the iterator.
     * @since Commons Collections 2.1.1 and 3.1
     */
    public static final Iterator INSTANCE = RESETTABLE_INSTANCE;

    /**
     * Constructor.
     */
    protected EmptyIterator() {
        super();
    }

}
