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
 * Defines a collection that allows objects to be removed in some well-defined order.
 * <p>
 * The removal order can be based on insertion order (eg, a FIFO queue or a
 * LIFO stack), on access order (eg, an LRU cache), on some arbitrary comparator
 * (eg, a priority queue) or on any other well-defined ordering.
 * <p>
 * Note that the removal order is not necessarily the same as the iteration
 * order.  A <code>Buffer</code> implementation may have equivalent removal
 * and iteration orders, but this is not required.
 * <p>
 * This interface does not specify any behavior for 
 * {@link Object#equals(Object)} and {@link Object#hashCode} methods.  It
 * is therefore possible for a <code>Buffer</code> implementation to also
 * also implement {@link java.util.List}, {@link java.util.Set} or 
 * {@link Bag}.
 *
 * @since Commons Collections 2.1
 * @version $Revision: 1.10 $ $Date: 2004/02/18 01:15:42 $
 * 
 * @author Avalon
 * @author Berin Loritsch
 * @author Paul Jack
 * @author Stephen Colebourne
 */
public interface Buffer extends Collection {

    /**
     * Gets and removes the next object from the buffer.
     *
     * @return the next object in the buffer, which is also removed
     * @throws BufferUnderflowException if the buffer is already empty
     */
    Object remove();

    /**
     * Gets the next object from the buffer without removing it.
     *
     * @return the next object in the buffer, which is not removed
     * @throws BufferUnderflowException if the buffer is empty
     */
    Object get();

}
