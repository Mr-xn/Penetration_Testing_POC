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

import java.util.Collection;

import org.apache.commons.collections.Buffer;
import org.apache.commons.collections.BufferUnderflowException;

/**
 * Decorates another <code>Buffer</code> to make {@link #get()} and
 * {@link #remove()} block when the <code>Buffer</code> is empty.
 * <p>
 * If either <code>get</code> or <code>remove</code> is called on an empty
 * <code>Buffer</code>, the calling thread waits for notification that
 * an <code>add</code> or <code>addAll</code> operation has completed.
 * <p>
 * When one or more entries are added to an empty <code>Buffer</code>,
 * all threads blocked in <code>get</code> or <code>remove</code> are notified.
 * There is no guarantee that concurrent blocked <code>get</code> or 
 * <code>remove</code> requests will be "unblocked" and receive data in the 
 * order that they arrive.
 * <p>
 * This class is Serializable from Commons Collections 3.1.
 *
 * @since Commons Collections 3.0
 * @version $Revision: 1.7 $ $Date: 2004/06/03 22:02:13 $
 * 
 * @author Stephen Colebourne
 * @author Janek Bogucki
 * @author Phil Steitz
 */
public class BlockingBuffer extends SynchronizedBuffer {

    /** Serialization version */
    private static final long serialVersionUID = 1719328905017860541L;

    /**
     * Factory method to create a blocking buffer.
     * 
     * @param buffer  the buffer to decorate, must not be null
     * @return a new blocking Buffer
     * @throws IllegalArgumentException if buffer is null
     */
    public static Buffer decorate(Buffer buffer) {
        return new BlockingBuffer(buffer);
    }

    //-----------------------------------------------------------------------    
    /**
     * Constructor that wraps (not copies).
     * 
     * @param buffer  the buffer to decorate, must not be null
     * @throws IllegalArgumentException if the buffer is null
     */
    protected BlockingBuffer(Buffer buffer) {
        super(buffer);
    }

    //-----------------------------------------------------------------------
    public boolean add(Object o) {
        synchronized (lock) {
            boolean result = collection.add(o);
            notifyAll();
            return result;
        }
    }
    
    public boolean addAll(Collection c) {
        synchronized (lock) {
            boolean result = collection.addAll(c);
            notifyAll();
            return result;
        }
    }
    
    public Object get() {
        synchronized (lock) {
            while (collection.isEmpty()) {
                try {
                    wait();
                } catch (InterruptedException e) {
                    throw new BufferUnderflowException();
                }
            }
            return getBuffer().get();
        }
    }
    
    public Object remove() {
        synchronized (lock) {
            while (collection.isEmpty()) {
                try {
                    wait();
                } catch (InterruptedException e) {
                    throw new BufferUnderflowException();
                }
            }
            return getBuffer().remove();
        }
    }
    
}
