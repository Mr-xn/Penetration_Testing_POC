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
package org.apache.commons.collections.list;

import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.lang.ref.WeakReference;
import java.util.ArrayList;
import java.util.Collection;
import java.util.ConcurrentModificationException;
import java.util.Iterator;
import java.util.List;
import java.util.ListIterator;

/**
 * A <code>List</code> implementation with a <code>ListIterator</code> that
 * allows concurrent modifications to the underlying list.
 * <p>
 * This implementation supports all of the optional {@link List} operations.
 * It extends <code>AbstractLinkedList</code> and thus provides the
 * stack/queue/dequeue operations available in {@link java.util.LinkedList}.
 * <p>
 * The main feature of this class is the ability to modify the list and the
 * iterator at the same time. Both the {@link #listIterator()} and {@link #cursor()}
 * methods provides access to a <code>Cursor</code> instance which extends
 * <code>ListIterator</code>. The cursor allows changes to the list concurrent
 * with changes to the iterator. Note that the {@link #iterator()} method and
 * sublists  do <b>not</b> provide this cursor behaviour.
 * <p>
 * The <code>Cursor</code> class is provided partly for backwards compatibility
 * and partly because it allows the cursor to be directly closed. Closing the
 * cursor is optional because references are held via a <code>WeakReference</code>.
 * For most purposes, simply modify the iterator and list at will, and then let
 * the garbage collector to the rest.
 * <p>
 * <b>Note that this implementation is not synchronized.</b>
 *
 * @see java.util.LinkedList
 * @since Commons Collections 1.0
 * @version $Revision: 1.5 $ $Date: 2004/02/18 01:12:26 $
 * 
 * @author Rodney Waldhoff
 * @author Janek Bogucki
 * @author Simon Kitching
 * @author Stephen Colebourne
 */
public class CursorableLinkedList extends AbstractLinkedList implements Serializable {

    /** Ensure serialization compatibility */
    private static final long serialVersionUID = 8836393098519411393L;

    /** A list of the cursor currently open on this list */
    protected transient List cursors = new ArrayList();

    //-----------------------------------------------------------------------
    /**
     * Constructor that creates.
     */
    public CursorableLinkedList() {
        super();
        init(); // must call init() as use super();
    }

    /**
     * Constructor that copies the specified collection
     * 
     * @param coll  the collection to copy
     */
    public CursorableLinkedList(Collection coll) {
        super(coll);
    }

    /**
     * The equivalent of a default constructor called
     * by any constructor and by <code>readObject</code>.
     */
    protected void init() {
        super.init();
        cursors = new ArrayList();
    }

    //-----------------------------------------------------------------------
    /**
     * Returns an iterator that does <b>not</b> support concurrent modification.
     * <p>
     * If the underlying list is modified while iterating using this iterator
     * a ConcurrentModificationException will occur.
     * The cursor behaviour is available via {@link #listIterator()}.
     * 
     * @return a new iterator that does <b>not</b> support concurrent modification
     */
    public Iterator iterator() {
        return super.listIterator(0);
    }

    /**
     * Returns a cursor iterator that allows changes to the underlying list in parallel.
     * <p>
     * The cursor enables iteration and list changes to occur in any order without
     * invalidating the iterator (from one thread). When elements are added to the
     * list, an event is fired to all active cursors enabling them to adjust to the
     * change in the list.
     * <p>
     * When the "current" (i.e., last returned by {@link ListIterator#next}
     * or {@link ListIterator#previous}) element of the list is removed,
     * the cursor automatically adjusts to the change (invalidating the
     * last returned value such that it cannot be removed).
     * 
     * @return a new cursor iterator
     */
    public ListIterator listIterator() {
        return cursor(0);
    }

    /**
     * Returns a cursor iterator that allows changes to the underlying list in parallel.
     * <p>
     * The cursor enables iteration and list changes to occur in any order without
     * invalidating the iterator (from one thread). When elements are added to the
     * list, an event is fired to all active cursors enabling them to adjust to the
     * change in the list.
     * <p>
     * When the "current" (i.e., last returned by {@link ListIterator#next}
     * or {@link ListIterator#previous}) element of the list is removed,
     * the cursor automatically adjusts to the change (invalidating the
     * last returned value such that it cannot be removed).
     * 
     * @param fromIndex  the index to start from
     * @return a new cursor iterator
     */
    public ListIterator listIterator(int fromIndex) {
        return cursor(fromIndex);
    }

    /**
     * Returns a {@link Cursor} for iterating through the elements of this list.
     * <p>
     * A <code>Cursor</code> is a <code>ListIterator</code> with an additional
     * <code>close()</code> method. Calling this method immediately discards the
     * references to the cursor. If it is not called, then the garbage collector
     * will still remove the reference as it is held via a <code>WeakReference</code>.
     * <p>
     * The cursor enables iteration and list changes to occur in any order without
     * invalidating the iterator (from one thread). When elements are added to the
     * list, an event is fired to all active cursors enabling them to adjust to the
     * change in the list.
     * <p>
     * When the "current" (i.e., last returned by {@link ListIterator#next}
     * or {@link ListIterator#previous}) element of the list is removed,
     * the cursor automatically adjusts to the change (invalidating the
     * last returned value such that it cannot be removed).
     * <p>
     * The {@link #listIterator()} method returns the same as this method, and can
     * be cast to a <code>Cursor</code> if the <code>close</code> method is required.
     *
     * @return a new cursor iterator
     */
    public CursorableLinkedList.Cursor cursor() {
        return cursor(0);
    }

    /**
     * Returns a {@link Cursor} for iterating through the elements of this list
     * starting from a specified index.
     * <p>
     * A <code>Cursor</code> is a <code>ListIterator</code> with an additional
     * <code>close()</code> method. Calling this method immediately discards the
     * references to the cursor. If it is not called, then the garbage collector
     * will still remove the reference as it is held via a <code>WeakReference</code>.
     * <p>
     * The cursor enables iteration and list changes to occur in any order without
     * invalidating the iterator (from one thread). When elements are added to the
     * list, an event is fired to all active cursors enabling them to adjust to the
     * change in the list.
     * <p>
     * When the "current" (i.e., last returned by {@link ListIterator#next}
     * or {@link ListIterator#previous}) element of the list is removed,
     * the cursor automatically adjusts to the change (invalidating the
     * last returned value such that it cannot be removed).
     * <p>
     * The {@link #listIterator(int)} method returns the same as this method, and can
     * be cast to a <code>Cursor</code> if the <code>close</code> method is required.
     *
     * @param fromIndex  the index to start from
     * @return a new cursor iterator
     * @throws IndexOutOfBoundsException if the index is out of range
     *      (index &lt; 0 || index &gt; size()).
     */
    public CursorableLinkedList.Cursor cursor(int fromIndex) {
        Cursor cursor = new Cursor(this, fromIndex);
        registerCursor(cursor);
        return cursor;
    }

    //-----------------------------------------------------------------------
    /**
     * Updates the node with a new value.
     * This implementation sets the value on the node.
     * Subclasses can override this to record the change.
     * 
     * @param node  node to update
     * @param value  new value of the node
     */
    protected void updateNode(Node node, Object value) {
        super.updateNode(node, value);
        broadcastNodeChanged(node);
    }

    /**
     * Inserts a new node into the list.
     *
     * @param nodeToInsert  new node to insert
     * @param insertBeforeNode  node to insert before
     * @throws NullPointerException if either node is null
     */
    protected void addNode(Node nodeToInsert, Node insertBeforeNode) {
        super.addNode(nodeToInsert, insertBeforeNode);
        broadcastNodeInserted(nodeToInsert);
    }
    
    /**
     * Removes the specified node from the list.
     *
     * @param node  the node to remove
     * @throws NullPointerException if <code>node</code> is null
     */
    protected void removeNode(Node node) {
        super.removeNode(node);
        broadcastNodeRemoved(node);
    }

    /**
     * Removes all nodes by iteration.
     */
    protected void removeAllNodes() {
        if (size() > 0) {
            // superclass implementation would break all the iterators
            Iterator it = iterator();
            while (it.hasNext()) {
                it.next();
                it.remove();
            }
        }
    }

    //-----------------------------------------------------------------------
    /**
     * Registers a cursor to be notified of changes to this list.
     * 
     * @param cursor  the cursor to register
     */
    protected void registerCursor(Cursor cursor) {
        // We take this opportunity to clean the cursors list
        // of WeakReference objects to garbage-collected cursors.
        for (Iterator it = cursors.iterator(); it.hasNext();) {
            WeakReference ref = (WeakReference) it.next();
            if (ref.get() == null) {
                it.remove();
            }
        }
        cursors.add(new WeakReference(cursor));
    }

    /**
     * Deregisters a cursor from the list to be notified of changes.
     * 
     * @param cursor  the cursor to deregister
     */
    protected void unregisterCursor(Cursor cursor) {
        for (Iterator it = cursors.iterator(); it.hasNext();) {
            WeakReference ref = (WeakReference) it.next();
            Cursor cur = (Cursor) ref.get();
            if (cur == null) {
                // some other unrelated cursor object has been 
                // garbage-collected; let's take the opportunity to
                // clean up the cursors list anyway..
                it.remove();

            } else if (cur == cursor) {
                ref.clear();
                it.remove();
                break;
            }
        }
    }

    //-----------------------------------------------------------------------
    /**
     * Informs all of my registered cursors that the specified
     * element was changed.
     * 
     * @param node  the node that was changed
     */
    protected void broadcastNodeChanged(Node node) {
        Iterator it = cursors.iterator();
        while (it.hasNext()) {
            WeakReference ref = (WeakReference) it.next();
            Cursor cursor = (Cursor) ref.get();
            if (cursor == null) {
                it.remove(); // clean up list
            } else {
                cursor.nodeChanged(node);
            }
        }
    }

    /**
     * Informs all of my registered cursors that the specified
     * element was just removed from my list.
     * 
     * @param node  the node that was changed
     */
    protected void broadcastNodeRemoved(Node node) {
        Iterator it = cursors.iterator();
        while (it.hasNext()) {
            WeakReference ref = (WeakReference) it.next();
            Cursor cursor = (Cursor) ref.get();
            if (cursor == null) {
                it.remove(); // clean up list
            } else {
                cursor.nodeRemoved(node);
            }
        }
    }

    /**
     * Informs all of my registered cursors that the specified
     * element was just added to my list.
     * 
     * @param node  the node that was changed
     */
    protected void broadcastNodeInserted(Node node) {
        Iterator it = cursors.iterator();
        while (it.hasNext()) {
            WeakReference ref = (WeakReference) it.next();
            Cursor cursor = (Cursor) ref.get();
            if (cursor == null) {
                it.remove(); // clean up list
            } else {
                cursor.nodeInserted(node);
            }
        }
    }

    //-----------------------------------------------------------------------
    /**
     * Serializes the data held in this object to the stream specified.
     */
    private void writeObject(ObjectOutputStream out) throws IOException {
        out.defaultWriteObject();
        doWriteObject(out);
    }

    /**
     * Deserializes the data held in this object to the stream specified.
     */
    private void readObject(ObjectInputStream in) throws IOException, ClassNotFoundException {
        in.defaultReadObject();
        doReadObject(in);
    }

    //-----------------------------------------------------------------------
    /**
     * An extended <code>ListIterator</code> that allows concurrent changes to
     * the underlying list.
     */
    public static class Cursor extends AbstractLinkedList.LinkedListIterator {
        /** Is the cursor valid (not closed) */
        boolean valid = true;
        /** Is the next index valid */
        boolean nextIndexValid = true;
        
        /**
         * Constructs a new cursor.
         * 
         * @param index  the index to start from
         */
        protected Cursor(CursorableLinkedList parent, int index) {
            super(parent, index);
            valid = true;
        }
        
        /**
         * Adds an object to the list.
         * The object added here will be the new 'previous' in the iterator.
         * 
         * @param obj  the object to add
         */
        public void add(Object obj) {
            super.add(obj);
            // add on iterator does not return the added element
            next = next.next;
        }

        /**
         * Gets the index of the next element to be returned.
         * 
         * @return the next index
         */
        public int nextIndex() {
            if (nextIndexValid == false) {
                if (next == parent.header) {
                    nextIndex = parent.size();
                } else {
                    int pos = 0;
                    Node temp = parent.header.next;
                    while (temp != next) {
                        pos++;
                        temp = temp.next;
                    }
                    nextIndex = pos;
                }
                nextIndexValid = true;
            }
            return nextIndex;
        }

        /**
         * Handle event from the list when a node has changed.
         * 
         * @param node  the node that changed
         */
        protected void nodeChanged(Node node) {
            // do nothing
        }

        /**
         * Handle event from the list when a node has been removed.
         * 
         * @param node  the node that was removed
         */
        protected void nodeRemoved(Node node) {
            if (node == next) {
                next = node.next;
            } else if (node == current) {
                current = null;
                nextIndex--;
            } else {
                nextIndexValid = false;
            }
        }

        /**
         * Handle event from the list when a node has been added.
         * 
         * @param node  the node that was added
         */
        protected void nodeInserted(Node node) {
            if (node.previous == current) {
                next = node;
            } else if (next.previous == node) {
                next = node;
            } else {
                nextIndexValid = false;
            }
        }

        /**
         * Override superclass modCount check, and replace it with our valid flag.
         */
        protected void checkModCount() {
            if (!valid) {
                throw new ConcurrentModificationException("Cursor closed");
            }
        }

        /**
         * Mark this cursor as no longer being needed. Any resources
         * associated with this cursor are immediately released.
         * In previous versions of this class, it was mandatory to close
         * all cursor objects to avoid memory leaks. It is <i>no longer</i>
         * necessary to call this close method; an instance of this class
         * can now be treated exactly like a normal iterator.
         */
        public void close() {
            if (valid) {
                ((CursorableLinkedList) parent).unregisterCursor(this);
                valid = false;
            }
        }
    }
}
