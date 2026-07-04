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
import java.util.HashMap;

/**
 * A {@link Bag} that is backed by a {@link HashMap}.
 *
 * @deprecated Moved to bag subpackage and rewritten internally. Due to be removed in v4.0.
 * @since Commons Collections 2.0
 * @version $Revision: 1.13 $ $Date: 2004/02/18 01:15:42 $
 * 
 * @author Chuck Burdick
 */
public class HashBag extends DefaultMapBag implements Bag {

    /**
     * Constructs an empty <Code>HashBag</Code>.
     */
    public HashBag() {
        super(new HashMap());
    }

    /**
     * Constructs a {@link Bag} containing all the members of the given
     * collection.
     * 
     * @param coll  a collection to copy into this bag
     */
    public HashBag(Collection coll) {
        this();
        addAll(coll);
    }

}
