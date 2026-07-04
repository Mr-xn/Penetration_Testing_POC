/*
 *  Copyright 2002-2004 The Apache Software Foundation
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
package org.apache.commons.collections;

import java.util.Collection;

/**
 * Defines a collection that is bounded in size.
 * <p>
 * The size of the collection can vary, but it can never exceed a preset 
 * maximum number of elements. This interface allows the querying of details
 * associated with the maximum number of elements.
 *
 * @see CollectionUtils#isFull
 * @see CollectionUtils#maxSize
 *
 * @since Commons Collections 3.0
 * @version $Revision: 1.11 $ $Date: 2004/04/14 20:13:11 $
 * 
 * @author Herve Quiroz
 * @author Stephen Colebourne
 */
public interface BoundedCollection extends Collection {

    /**
     * Returns true if this collection is full and no new elements can be added.
     *
     * @return <code>true</code> if the collection is full
     */
    boolean isFull();

    /**
     * Gets the maximum size of the collection (the bound).
     *
     * @return the maximum number of elements the collection can hold
     */
    int maxSize();

}
