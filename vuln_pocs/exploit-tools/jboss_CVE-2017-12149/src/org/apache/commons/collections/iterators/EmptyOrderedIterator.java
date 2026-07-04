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

import org.apache.commons.collections.OrderedIterator;
import org.apache.commons.collections.ResettableIterator;

/** 
 * Provides an implementation of an empty ordered iterator.
 *
 * @since Commons Collections 3.1
 * @version $Revision: 1.1 $ $Date: 2004/05/26 21:52:40 $
 * 
 * @author Stephen Colebourne
 */
public class EmptyOrderedIterator extends AbstractEmptyIterator implements OrderedIterator, ResettableIterator {

    /**
     * Singleton instance of the iterator.
     * @since Commons Collections 3.1
     */
    public static final OrderedIterator INSTANCE = new EmptyOrderedIterator();

    /**
     * Constructor.
     */
    protected EmptyOrderedIterator() {
        super();
    }

}
