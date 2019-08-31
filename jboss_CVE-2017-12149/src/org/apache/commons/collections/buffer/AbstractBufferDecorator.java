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
package org.apache.commons.collections.buffer;

import org.apache.commons.collections.Buffer;
import org.apache.commons.collections.collection.AbstractCollectionDecorator;

/**
 * Decorates another <code>Buffer</code> to provide additional behaviour.
 * <p>
 * Methods are forwarded directly to the decorated buffer.
 *
 * @since Commons Collections 3.0
 * @version $Revision: 1.4 $ $Date: 2004/06/02 21:53:02 $
 * 
 * @author Stephen Colebourne
 */
public abstract class AbstractBufferDecorator extends AbstractCollectionDecorator implements Buffer {

    /**
     * Constructor only used in deserialization, do not use otherwise.
     * @since Commons Collections 3.1
     */
    protected AbstractBufferDecorator() {
        super();
    }

    /**
     * Constructor that wraps (not copies).
     * 
     * @param buffer  the buffer to decorate, must not be null
     * @throws IllegalArgumentException if list is null
     */
    protected AbstractBufferDecorator(Buffer buffer) {
        super(buffer);
    }

    /**
     * Gets the buffer being decorated.
     * 
     * @return the decorated buffer
     */
    protected Buffer getBuffer() {
        return (Buffer) getCollection();
    }

    //-----------------------------------------------------------------------
    public Object get() {
        return getBuffer().get();
    }

    public Object remove() {
        return getBuffer().remove();
    }

}
