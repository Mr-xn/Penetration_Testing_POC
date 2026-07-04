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
package org.apache.commons.collections.bag;

import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.util.Collection;
import java.util.HashMap;

import org.apache.commons.collections.Bag;

/**
 * Implements <code>Bag</code>, using a <code>HashMap</code> to provide the
 * data storage. This is the standard implementation of a bag.
 * <p>
 * A <code>Bag</code> stores each object in the collection together with a
 * count of occurrences. Extra methods on the interface allow multiple copies
 * of an object to be added or removed at once. It is important to read the
 * interface javadoc carefully as several methods violate the
 * <code>Collection</code> interface specification.
 *
 * @since Commons Collections 3.0 (previously in main package v2.0)
 * @version $Revision: 1.8 $ $Date: 2004/02/18 00:56:25 $
 * 
 * @author Chuck Burdick
 * @author Stephen Colebourne
 */
public class HashBag
        extends AbstractMapBag implements Bag, Serializable {

    /** Serial version lock */
    static final long serialVersionUID = -6561115435802554013L;
    
    /**
     * Constructs an empty <code>HashBag</code>.
     */
    public HashBag() {
        super(new HashMap());
    }

    /**
     * Constructs a bag containing all the members of the given collection.
     * 
     * @param coll  a collection to copy into this bag
     */
    public HashBag(Collection coll) {
        this();
        addAll(coll);
    }

    //-----------------------------------------------------------------------
    /**
     * Write the bag out using a custom routine.
     */
    private void writeObject(ObjectOutputStream out) throws IOException {
        out.defaultWriteObject();
        super.doWriteObject(out);
    }

    /**
     * Read the bag in using a custom routine.
     */
    private void readObject(ObjectInputStream in) throws IOException, ClassNotFoundException {
        in.defaultReadObject();
        super.doReadObject(new HashMap(), in);
    }
    
}
