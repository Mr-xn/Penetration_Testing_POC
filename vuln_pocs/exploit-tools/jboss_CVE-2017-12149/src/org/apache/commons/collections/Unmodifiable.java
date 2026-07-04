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
package org.apache.commons.collections;

/**
 * Marker interface for collections, maps and iterators that are unmodifiable.
 * <p>
 * This interface enables testing such as:
 * <pre>
 * if (coll instanceof Unmodifiable) {
 *   coll = new ArrayList(coll);
 * }
 * // now we know coll is modifiable
 * </pre>
 * Of course all this only works if you use the Unmodifiable classes defined
 * in this library. If you use the JDK unmodifiable class via java util Collections
 * then the interface won't be there.
 *  
 * @since Commons Collections 3.0
 * @version $Revision: 1.4 $ $Date: 2004/02/18 01:15:42 $
 *
 * @author Stephen Colebourne
 */
public interface Unmodifiable {
    // marker interface - no methods to implement
}
