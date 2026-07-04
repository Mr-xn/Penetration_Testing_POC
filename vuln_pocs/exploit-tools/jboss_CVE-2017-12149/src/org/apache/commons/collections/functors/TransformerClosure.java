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

import org.apache.commons.collections.Closure;
import org.apache.commons.collections.Transformer;

/**
 * Closure implementation that calls a Transformer using the input object
 * and ignore the result.
 * 
 * @since Commons Collections 3.0
 * @version $Revision: 1.5 $ $Date: 2004/05/16 11:47:38 $
 *
 * @author Stephen Colebourne
 */
public class TransformerClosure implements Closure, Serializable {

    /** Serial version UID */
    static final long serialVersionUID = -5194992589193388969L;

    /** The transformer to wrap */
    private final Transformer iTransformer;

    /**
     * Factory method that performs validation.
     * <p>
     * A null transformer will return the <code>NOPClosure</code>.
     * 
     * @param transformer  the transformer to call, null means nop
     * @return the <code>transformer</code> closure
     */
    public static Closure getInstance(Transformer transformer) {
        if (transformer == null) {
            return NOPClosure.INSTANCE;
        }
        return new TransformerClosure(transformer);
    }

    /**
     * Constructor that performs no validation.
     * Use <code>getInstance</code> if you want that.
     * 
     * @param transformer  the transformer to call, not null
     */
    public TransformerClosure(Transformer transformer) {
        super();
        iTransformer = transformer;
    }

    /**
     * Executes the closure by calling the decorated transformer.
     * 
     * @param input  the input object
     */
    public void execute(Object input) {
        iTransformer.transform(input);
    }

    /**
     * Gets the transformer.
     * 
     * @return the transformer
     * @since Commons Collections 3.1
     */
    public Transformer getTransformer() {
        return iTransformer;
    }

}
