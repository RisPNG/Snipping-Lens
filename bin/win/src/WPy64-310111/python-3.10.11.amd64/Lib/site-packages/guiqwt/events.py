# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

# pylint: disable-msg=W0622,R0903
# W0622: complains about filter being a builtin
# R0903: complains about too few public methods which is the purpose here

"""
guiqwt.events
-------------

The `event` module handles event management (states, event filter, ...).
"""


import weakref
from qtpy.QtCore import QEvent, Qt, QObject, QPointF, Signal
from qtpy.QtGui import QKeySequence

CursorShape = type(Qt.ArrowCursor)

from guiqwt.config import CONF
from guiqwt.debug import evt_type_to_str, buttons_to_str


# Sélection d'événements  ---------
class EventMatch(object):
    """A callable returning true if it matches an event"""

    def __call__(self, event):
        raise NotImplementedError

    def get_event_types(self):
        """Returns a set of event types handled by this
        EventMatch.
        This is used to quickly optimize events not handled
        by any event matchers
        """
        return frozenset()


class KeyEventMatch(EventMatch):
    """
    A callable returning True if it matches a key event
    keys: list of keys or couples (key, modifier)
    """

    def __init__(self, keys):
        super(KeyEventMatch, self).__init__()
        key_list, mod_list = [], []
        for item in keys:
            if isinstance(item, (tuple, list)):
                k, m = item
            else:
                k = item
                # Avoid bad arguments: modifier instead of key
                assert k not in (
                    Qt.ControlModifier,
                    Qt.ShiftModifier,
                    Qt.AltModifier,
                    Qt.NoModifier,
                )
                m = Qt.NoModifier
            key_list.append(k)
            mod_list.append(m)
        self.keys = key_list
        self.mods = mod_list

    def get_event_types(self):
        return frozenset((QEvent.KeyPress,))

    def __call__(self, event):
        if event.type() == QEvent.KeyPress:
            my_key = event.key()
            my_mod = event.modifiers()
            if my_key in self.keys:
                mod = self.mods[self.keys.index(my_key)]
                if mod == Qt.NoModifier or my_mod & mod:
                    return True
        return False


class StandardKeyMatch(EventMatch):
    """
    A callable returning True if it matches a key event
    keysequence: QKeySequence.StandardKey integer
    """

    def __init__(self, keysequence):
        super(StandardKeyMatch, self).__init__()
        assert isinstance(keysequence, (int, QKeySequence.StandardKey))
        self.keyseq = keysequence

    def get_event_types(self):
        return frozenset((QEvent.KeyPress,))

    def __call__(self, event):
        return event.type() == QEvent.KeyPress and event.matches(self.keyseq)


class MouseEventMatch(EventMatch):
    """Base class for matching mouse events"""

    def __init__(self, evt_type, btn, modifiers=Qt.NoModifier):
        super(MouseEventMatch, self).__init__()
        assert isinstance(modifiers, (int, Qt.KeyboardModifiers, Qt.KeyboardModifier))
        self.evt_type = evt_type
        self.button = btn
        self.modifiers = modifiers

    def get_event_types(self):
        return frozenset((self.evt_type,))

    def __call__(self, event):
        if event.type() == self.evt_type:
            if event.button() == self.button:
                if self.modifiers != Qt.NoModifier:
                    if (event.modifiers() & self.modifiers) == self.modifiers:
                        return True
                elif event.modifiers() == Qt.NoModifier:
                    return True
        return False

    def __repr__(self):
        return "<MouseMatch: %s/ %08x:%s>" % (
            evt_type_to_str(self.evt_type),
            self.modifiers,
            buttons_to_str(self.button),
        )


class MouseMoveMatch(MouseEventMatch):
    def __call__(self, event):
        if event.type() == self.evt_type:
            if (
                self.button != Qt.NoButton
                and (event.buttons() & self.button == self.button)
            ) or event.buttons() == Qt.NoButton:
                if self.modifiers != Qt.NoModifier:
                    if (event.modifiers() & self.modifiers) == self.modifiers:
                        return True
                elif event.modifiers() == Qt.NoModifier:
                    return True
        return False


# Machine d'état  ----------
class StatefulEventFilter(QObject):
    """Gestion d'une machine d'état pour les événements
    d'un canvas
    """

    def __init__(self, parent):
        super(StatefulEventFilter, self).__init__()
        self.states = {0: {}}  # 0 : cursor 1: panning, 2: zooming
        self.cursors = {}
        self.state = 0
        self.max_state = 0
        self.events = {}
        self.plot = parent
        self.all_event_types = frozenset()

    def eventFilter(self, _obj, event):
        """Le callback 'eventfilter' pour Qt"""
        if not hasattr(self, "all_event_types"):
            print(repr(self), self)
        if event.type() not in self.all_event_types:
            return False

        state = self.states[self.state]
        #        from pprint import pprint
        #        print self.state
        #        pprint(state.keys())
        for match, (call_list, next_state) in list(state.items()):
            if match(event):
                self.set_state(next_state, event)
                for call in call_list:
                    call(self, event)  # might change state
        return False

    def set_state(self, state, event):
        """Change l'état courant.

        Peut être appelé par les handlers pour annuler un
        changement d'état"""
        assert state in self.states
        if state == self.state:
            return
        self.state = state
        cursor = self.get_cursor(event)
        if cursor is not None:
            self.plot.canvas().setCursor(cursor)

    def new_state(self):
        """Création (réservation) d'un nouveau numéro d'état"""
        self.max_state += 1
        self.states[self.max_state] = {}
        return self.max_state

    def add_event(self, state, match, call, next_state=None):
        """Ajoute une transition sur la machine d'état
        si next_state est fourni, il doit correspondre à un état existant
        sinon un nouvel état d'arrivée est créé
        """
        assert isinstance(state, int)
        assert isinstance(match, EventMatch)
        self.all_event_types = self.all_event_types.union(match.get_event_types())
        entry = self.states[state].setdefault(match, [[], None])
        entry[0].append(call)
        if entry[1] is None:
            if next_state is None:
                next_state = self.new_state()
            else:
                pass
        else:
            if next_state is not None:
                assert next_state == entry[1]
            else:
                next_state = entry[1]

        entry[1] = next_state
        return next_state

    # gestion du curseur
    def set_cursor(self, cursor, *states):
        """Associe un curseur à un ou plusieurs états"""
        assert isinstance(cursor, CursorShape)
        for s in states:
            self.cursors[s] = cursor

    def get_cursor(self, _event):
        """Récupère le curseur associé à un état / événement donné"""
        # on passe event pour eventuellement pouvoir choisir
        # le curseur en fonction des touches de modification
        cursor = self.cursors.get(self.state, None)
        if cursor is None:
            # no cursor specified : should keep previous one
            return None
        return cursor

    # Fonction utilitaires
    def mouse_press(self, btn, modifiers=Qt.NoModifier):
        """Création d'un filtre pour l'événement MousePress"""
        return self.events.setdefault(
            ("mousepress", btn, modifiers),
            MouseEventMatch(QEvent.MouseButtonPress, btn, modifiers),
        )

    def mouse_move(self, btn, modifiers=Qt.NoModifier):
        """Création d'un filtre pour l'événement MouseMove"""
        return self.events.setdefault(
            ("mousemove", btn, modifiers),
            MouseMoveMatch(QEvent.MouseMove, btn, modifiers),
        )

    def mouse_release(self, btn, modifiers=Qt.NoModifier):
        """Création d'un filtre pour l'événement MouseRelease"""
        return self.events.setdefault(
            ("mouserelease", btn, modifiers),
            MouseEventMatch(QEvent.MouseButtonRelease, btn, modifiers),
        )

    def nothing(self, filter, event):
        """A nothing filter, provided to help removing duplicate handlers"""
        pass


class DragHandler(QObject):
    """Classe de base pour les gestionnaires d'événements du type
    click - drag - release
    """

    cursor = None

    def __init__(self, filter, btn, mods=Qt.NoModifier, start_state=0):
        super(DragHandler, self).__init__()
        self.state0 = filter.add_event(
            start_state, filter.mouse_press(btn, mods), self.start_tracking
        )
        self.state1 = filter.add_event(
            self.state0, filter.mouse_move(btn, mods), self.start_moving
        )
        filter.add_event(
            self.state1, filter.mouse_move(btn, mods), self.move, self.state1
        )
        filter.add_event(
            self.state0,
            filter.mouse_release(btn, mods),
            self.stop_notmoving,
            start_state,
        )
        filter.add_event(
            self.state1, filter.mouse_release(btn, mods), self.stop_moving, start_state
        )
        if self.cursor is not None:
            filter.set_cursor(self.cursor, self.state0, self.state1)
        self.start = None  # first mouse position
        self.last = None  # mouse position seen during last event
        self.parent_tracking = None

    def get_move_state(self, filter, pos):
        rct = filter.plot.contentsRect()
        dx = (pos.x(), self.last.x(), self.start.x(), rct.width())
        dy = (pos.y(), self.last.y(), self.start.y(), rct.height())
        self.last = QPointF(pos)
        return dx, dy

    def start_tracking(self, _filter, event):
        self.start = self.last = QPointF(event.pos())

    def start_moving(self, filter, event):
        return self.move(filter, event)

    def stop_tracking(self, _filter, _event):
        pass
        # filter.plot.canvas().setMouseTracking(self.parent_tracking)

    def stop_notmoving(self, filter, event):
        self.stop_tracking(filter, event)

    def stop_moving(self, filter, event):
        self.stop_tracking(filter, event)

    def move(self, filter, event):
        raise NotImplementedError()


class ClickHandler(QObject):
    """Classe de base pour les gestionnaires d'événements du type
    click - release
    """

    #: Signal emitted by ClickHandler on mouse click
    SIG_CLICK_EVENT = Signal(object, "QEvent")

    def __init__(self, filter, btn, mods=Qt.NoModifier, start_state=0):
        super(ClickHandler, self).__init__()
        self.state0 = filter.add_event(
            start_state, filter.mouse_press(btn, mods), filter.nothing
        )
        filter.add_event(
            self.state0, filter.mouse_release(btn, mods), self.click, start_state
        )

    def click(self, filter, event):
        self.SIG_CLICK_EVENT.emit(filter, event)


class PanHandler(DragHandler):
    cursor = Qt.ClosedHandCursor

    def move(self, filter, event):
        x_state, y_state = self.get_move_state(filter, event.pos())
        filter.plot.do_pan_view(x_state, y_state)


class ZoomHandler(DragHandler):
    cursor = Qt.SizeAllCursor

    def move(self, filter, event):
        x_state, y_state = self.get_move_state(filter, event.pos())
        filter.plot.do_zoom_view(x_state, y_state)


class MenuHandler(ClickHandler):
    def click(self, filter, event):
        menu = filter.plot.get_context_menu()
        if menu:
            menu.popup(event.globalPos())


class QtDragHandler(DragHandler):

    #: Signal emitted by QtDragHandler when starting tracking
    SIG_START_TRACKING = Signal(object, "QEvent")

    #: Signal emitted by QtDragHandler when stopping tracking and not moving
    SIG_STOP_NOT_MOVING = Signal(object, "QEvent")

    #: Signal emitted by QtDragHandler when stopping tracking and moving
    SIG_STOP_MOVING = Signal(object, "QEvent")

    #: Signal emitted by QtDragHandler when moving
    SIG_MOVE = Signal(object, "QEvent")

    def start_tracking(self, filter, event):
        DragHandler.start_tracking(self, filter, event)
        self.SIG_START_TRACKING.emit(filter, event)

    def stop_notmoving(self, filter, event):
        self.SIG_STOP_NOT_MOVING.emit(filter, event)

    def stop_moving(self, filter, event):
        self.SIG_STOP_MOVING.emit(filter, event)

    def move(self, filter, event):
        self.SIG_MOVE.emit(filter, event)


class AutoZoomHandler(ClickHandler):
    def click(self, filter, _event):
        filter.plot.do_autoscale()


class MoveHandler(object):
    def __init__(self, filter, btn=Qt.NoButton, mods=Qt.NoModifier, start_state=0):
        filter.add_event(
            start_state, filter.mouse_move(btn, mods), self.move, start_state
        )

    def move(self, filter, event):
        filter.plot.do_move_marker(event)


class UndoMoveObject(object):
    def __init__(self, obj, pos1, pos2):
        self.obj = obj
        from guiqwt.baseplot import canvas_to_axes

        self.coords1 = canvas_to_axes(obj, pos1)
        self.coords2 = canvas_to_axes(obj, pos2)

    def is_valid(self):
        return self.obj.plot() is not None

    def compute_positions(self):
        from guiqwt.baseplot import axes_to_canvas

        pos1 = QPointF(*axes_to_canvas(self.obj, *self.coords1))
        pos2 = QPointF(*axes_to_canvas(self.obj, *self.coords2))
        return pos1, pos2

    def undo(self):
        pos1, pos2 = self.compute_positions()
        self.obj.plot().unselect_all()
        self.obj.move_local_shape(pos1, pos2)

    def redo(self):
        pos1, pos2 = self.compute_positions()
        self.obj.plot().unselect_all()
        self.obj.move_local_shape(pos2, pos1)


class UndoMovePoint(UndoMoveObject):
    def __init__(self, obj, pos1, pos2, handle, ctrl):
        super(UndoMovePoint, self).__init__(obj, pos1, pos2)
        self.handle = handle
        self.ctrl = ctrl

    def undo(self):
        pos1, pos2 = self.compute_positions()
        self.obj.move_local_point_to(self.handle, pos1, self.ctrl)

    def redo(self):
        pos1, pos2 = self.compute_positions()
        self.obj.move_local_point_to(self.handle, pos2, self.ctrl)


class ObjectHandler(object):
    def __init__(
        self, filter, btn, mods=Qt.NoModifier, start_state=0, multiselection=False
    ):
        self.multiselection = multiselection
        self.start_state = start_state
        self.state0 = filter.add_event(
            start_state, filter.mouse_press(btn, mods), self.start_tracking
        )
        filter.add_event(
            self.state0, filter.mouse_move(btn, mods), self.move, self.state0
        )
        filter.add_event(
            self.state0,
            filter.mouse_release(btn, mods),
            self.stop_tracking,
            start_state,
        )
        filter.add_event(
            start_state, StandardKeyMatch(QKeySequence.Undo), self.undo, start_state
        )
        filter.add_event(
            start_state, StandardKeyMatch(QKeySequence.Redo), self.redo, start_state
        )
        self.handle = None  # first mouse position
        self.inside = False
        self._active = None  # mouse position seen during last event
        self.last_pos = None
        self.unselection_pending = None

        self.undo_stack = [None]
        self.undo_index = 0
        self.first_pos = None
        self.undo_action = None

    @property
    def active(self):
        if self._active is not None:
            return self._active()

    @active.setter
    def active(self, value):
        if value is None:
            self._active = None
        else:
            self._active = weakref.ref(value)

    def add_undo_move_action(self, undo_action):
        self.undo_stack = self.undo_stack[: self.undo_index + 1]
        self.undo_stack.append(undo_action)
        self.undo_index = len(self.undo_stack) - 1

    def undo(self, filter, event):
        action = self.undo_stack[self.undo_index]
        if action is not None:
            if action.is_valid():
                action.undo()
                filter.plot.replot()
            else:
                self.undo_stack.remove(action)
            self.undo_index -= 1

    def redo(self, filter, event):
        if self.undo_index < len(self.undo_stack) - 1:
            action = self.undo_stack[self.undo_index + 1]
            if action.is_valid():
                action.redo()
                filter.plot.replot()
                self.undo_index += 1
            else:
                self.undo_stack.remove(action)

    def start_tracking(self, filter, event):
        plot = filter.plot
        self.inside = False
        self.active = None
        self.handle = None
        self.first_pos = pos = event.pos()
        self.last_pos = QPointF(pos)
        selected = plot.get_active_item()
        distance = CONF.get("plot", "selection/distance", 6)

        (
            nearest,
            nearest_dist,
            nearest_handle,
            nearest_inside,
        ) = plot.get_nearest_object(pos, distance)
        if nearest is not None:
            # Is the nearest object the real deal?
            if not nearest.can_select() or nearest_dist >= distance:
                # Looking for the nearest object in z containing cursor position
                (
                    nearest,
                    nearest_dist,
                    nearest_handle,
                    nearest_inside,
                ) = plot.get_nearest_object_in_z(pos)

        # This will unselect active item only if it's not moved afterwards:
        self.unselection_pending = selected is nearest
        if selected and not self.multiselection:
            # An item is selected
            self.active = selected
            (dist, self.handle, self.inside, other_object) = self.active.hit_test(pos)
            if other_object is not None:
                # e.g. LegendBoxItem: 'other_object' is the selected curve
                plot.set_active_item(other_object)
                return
            if dist >= distance and not self.inside:
                # The following allows to move together selected items by
                # clicking inside any of them (instead of active item only)
                other_selitems = [
                    _it
                    for _it in plot.get_selected_items()
                    if _it is not self.active and _it.can_move()
                ]
                for selitem in other_selitems:
                    dist, handle, inside, _other = selitem.hit_test(pos)
                    if dist < distance or inside:
                        self.inside = inside
                        break
                else:
                    self.__unselect_objects(filter)
                    filter.set_state(self.start_state, event)
                    return
        else:
            # No item is selected
            self.active = nearest
            self.handle = nearest_handle
            self.inside = nearest_inside
            dist = nearest_dist
            if nearest is not None:
                plot.set_active_item(nearest)
                if not nearest.selected:
                    if not self.multiselection:
                        plot.unselect_all()
                    plot.select_item(nearest)

        # Eventually move or resize selected object:
        self.__move_or_resize_object(dist, distance, event, filter)
        plot.replot()

    def __unselect_objects(self, filter):
        """Unselect selected object*s*"""
        plot = filter.plot
        plot.unselect_all()
        plot.replot()

    def __move_or_resize_object(self, dist, distance, event, filter):
        if (
            dist < distance
            and self.handle is not None
            and (self.active.can_resize() or self.active.can_rotate())
        ):
            # Resize / move handle
            self.inside = False
            return
        if self.inside and self.active.can_move():
            # Move object
            return
        # can't move, can't resize
        filter.set_state(self.start_state, event)
        if self.unselection_pending:
            self.__unselect_objects(filter)

    def move(self, filter, event):
        if self.active is None:
            return
        self.unselection_pending = False
        if self.inside:
            self.active.move_local_shape(self.last_pos, event.pos())
            self.undo_action = UndoMoveObject(self.active, event.pos(), self.first_pos)
        else:
            ctrl = event.modifiers() & Qt.ControlModifier == Qt.ControlModifier
            self.active.move_local_point_to(self.handle, event.pos(), ctrl)
            self.undo_action = UndoMovePoint(
                self.active, self.first_pos, event.pos(), self.handle, ctrl
            )
        self.last_pos = QPointF(event.pos())
        filter.plot.replot()

    def stop_tracking(self, filter, event):
        self.add_undo_move_action(self.undo_action)
        if self.unselection_pending:
            self.__unselect_objects(filter)
        self.handle = None
        self.active = None


class RectangularSelectionHandler(DragHandler):

    #: Signal emitted by RectangularSelectionHandler when ending selection
    SIG_END_RECT = Signal(object, "QPointF", "QPointF")

    def __init__(self, filter, btn, mods=Qt.NoModifier, start_state=0):
        super(RectangularSelectionHandler, self).__init__(
            filter, btn, mods, start_state
        )
        self.avoid_null_shape = False

    def set_shape(self, shape, h0, h1, setup_shape_cb=None, avoid_null_shape=False):
        self.shape = shape
        self.shape_h0 = h0
        self.shape_h1 = h1
        self.setup_shape_cb = setup_shape_cb
        self.avoid_null_shape = avoid_null_shape

    def start_tracking(self, filter, event):
        self.start = self.last = QPointF(event.pos())

    def start_moving(self, filter, event):
        self.shape.attach(filter.plot)
        self.shape.setZ(filter.plot.get_max_z() + 1)
        if self.avoid_null_shape:
            self.start -= QPointF(1, 1)
        self.shape.move_local_point_to(self.shape_h0, self.start)
        self.shape.move_local_point_to(self.shape_h1, event.pos())
        self.start_moving_action(filter, event)
        if self.setup_shape_cb is not None:
            self.setup_shape_cb(self.shape)
        self.shape.show()
        filter.plot.replot()

    def start_moving_action(self, filter, event):
        """Les classes derivees peuvent surcharger cette methode"""
        pass

    def move(self, filter, event):
        self.shape.move_local_point_to(self.shape_h1, event.pos())
        self.move_action(filter, event)
        filter.plot.replot()

    def move_action(self, filter, event):
        """Les classes derivees peuvent surcharger cette methode"""
        pass

    def stop_moving(self, filter, event):
        self.shape.detach()
        self.stop_moving_action(filter, event)
        filter.plot.replot()

    def stop_moving_action(self, filter, event):
        """Les classes derivees peuvent surcharger cette methode"""
        self.SIG_END_RECT.emit(filter, self.start, event.pos())


class PointSelectionHandler(RectangularSelectionHandler):
    def stop_notmoving(self, filter, event):
        self.stop_moving(filter, event)


class ZoomRectHandler(RectangularSelectionHandler):
    def stop_moving_action(self, filter, event):
        filter.plot.do_zoom_rect_view(self.start, event.pos())


def setup_standard_tool_filter(filter, start_state):
    """Création des filtres standard (pan/zoom) sur boutons milieu/droit"""
    # Bouton du milieu
    PanHandler(filter, Qt.MidButton, start_state=start_state)
    AutoZoomHandler(filter, Qt.MidButton, start_state=start_state)

    # Bouton droit
    ZoomHandler(filter, Qt.RightButton, start_state=start_state)
    MenuHandler(filter, Qt.RightButton, start_state=start_state)

    # Autres (touches, move)
    MoveHandler(filter, start_state=start_state)
    MoveHandler(filter, start_state=start_state, mods=Qt.ShiftModifier)
    MoveHandler(filter, start_state=start_state, mods=Qt.AltModifier)
    return start_state
