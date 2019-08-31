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
package org.apache.commons.collections.functors;

import java.io.Serializable;

import org.apache.commons.collections.FunctorException;
import org.apache.commons.collections.Transformer;

/**
 * Transformer implementation that always throws an exception.
 * 
 * @since Commons Collections 3.0
 * @version $Revision: 1.7 $ $Date: 2004/05/16 11:36:31 $
 *
 * @author Stephen Colebourne
 */
public final class ExceptionTransformer implements Transformer, Serializable {

    /** Serial version UID */
    static final long serialVersionUID = 7179106032121985545L;
    

    /** Singleton predicate instance */
    public static final Transformer INSTANCE = new ExceptionTransformer();

    /**
     * Factory returning the singleton instance.
     * 
     * @return the singleton instance
     * @since Commons Collections 3.1
     */
    public static Transformer getInstance() {
        return INSTANCE;
    }

    /**
     * Restricted constructor.
     */
    private ExceptionTransformer() {
        super();
    }

    /**
     * Transforms the input to result by cloning it.
     * 
     * @param input  the input object to transform
     * @return never
     * @throws FunctorException always
     */
    public Object transform(Object input) {
        throw new FunctorException("ExceptionTransformer invoked");
    }

}
