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
import java.util.Comparator;
import java.util.SortedMap;
import java.util.TreeMap;

import org.apache.commons.collections.SortedBag;

/**
 * Implements <code>SortedBag</code>, using a <code>TreeMap</code> to provide
 * the data storage. This is the standard implementation of a sorted bag.
 * <p>
 * Order will be maintained among the bag members and can be viewed through the
 * iterator.
 * <p>
 * A <code>Bag</code> stores each object in the collection together with a
 * count of occurrences. Extra methods on the interface allow multiple copies
 * of an object to be added or removed at once. It is important to read the
 * interface javadoc carefully as several methods violate the
 * <code>Collection</code> interface specification.
 *
 * @since Commons Collections 3.0 (previously in main package v2.0)
 * @version $Revision: 1.9 $ $Date: 2004/02/18 00:56:25 $
 * 
 * @author Chuck Burdick
 * @author Stephen Colebourne
 */
public class TreeBag
        extends AbstractMapBag implements SortedBag, Serializable {

    /** Serial version lock */
    static final long serialVersionUID = -7740146511091606676L;
    
    /**
     * Constructs an empty <code>TreeBag</code>.
     */
    public TreeBag() {
        super(new TreeMap());
    }

    /**
     * Constructs an empty bag that maintains order on its unique
     * representative members according to the given {@link Comparator}.
     * 
     * @param comparator  the comparator to use
     */
    public TreeBag(Comparator comparator) {
        super(new TreeMap(comparator));
    }

    /**
     * Constructs a <code>TreeBag</code> containing all the members of the
     * specified collection.
     * 
     * @param coll  the collection to copy into the bag
     */
    public TreeBag(Collection coll) {
        this();
        addAll(coll);
    }

    //-----------------------------------------------------------------------
    public Object first() {
        return ((SortedMap) getMap()).firstKey();
    }

    public Object last() {
        return ((SortedMap) getMap()).lastKey();
    }

    public Comparator comparator() {
        return ((SortedMap) getMap()).comparator();
    }

    //-----------------------------------------------------------------------
    /**
     * Write the bag out using a custom routine.
     */
    private void writeObject(ObjectOutputStream out) throws IOException {
        out.defaultWriteObject();
        out.writeObject(comparator());
        super.doWriteObject(out);
    }

    /**
     * Read the bag in using a custom routine.
     */
    private void readObject(ObjectInputStream in) throws IOException, ClassNotFoundException {
        in.defaultReadObject();
        Comparator comp = (Comparator) in.readObject();
        super.doReadObject(new TreeMap(comp), in);
    }
    
}
