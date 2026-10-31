"""Context menus for both dropdown lists and selected chips."""
from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox
from northdiary.services.label_definitions import delete_definition


def delete_from_widget(owner, kind, name):
    if not name:
        return
    window = owner
    while window is not None:
        repository = getattr(window, 'repository', None)
        if repository is not None and hasattr(repository, 'database'):
            break
        window = window.parentWidget()
    if window is None:
        return
    if QMessageBox.question(owner, '删除定义', f'删除「{name}」及所有引用？文章和人物会保留。') != QMessageBox.StandardButton.Yes:
        return
    # Save pending article changes first, so later autosave cannot resurrect a definition.
    main = window
    while main is not None and not hasattr(main, 'refresh_categories'):
        main = main.parentWidget()
    if main is not None and not main.save(True):
        return
    try:
        delete_definition(repository.database.connection, kind, name)
    except Exception as error:
        QMessageBox.warning(owner, '删除失败', str(error))
        return
    from northdiary.ui.tag_picker import TagPicker
    from northdiary.ui.category_picker import CategoryPicker
    for widget in QApplication.allWidgets():
        ancestor = widget
        same_database = False
        while ancestor is not None:
            repo = getattr(ancestor, 'repository', None)
            if repo is not None and getattr(repo, 'database', None) is repository.database:
                same_database = True
                break
            ancestor = ancestor.parentWidget()
        if not same_database:
            continue
        if isinstance(widget, CategoryPicker) and kind == 'categories':
            widget.catalog = [n for n in widget.catalog if n != name]
            if widget.value == name:
                widget.setText('')
            widget.refresh()
        elif isinstance(widget, TagPicker) and kind == ('relationships' if widget.owner_label == '人物' else 'tags'):
            widget.catalog = [n for n in widget.catalog if n != name]
            widget.normal_names = [n for n in widget.normal_names if n != name]
            widget.refresh()
    if main is not None:
        if kind == 'categories' and main.category == name: main.category = None
        if kind == 'tags' and main.tag == name: main.tag = None
        attribute = 'selected_categories' if kind == 'categories' else 'selected_tags' if kind == 'tags' else None
        if attribute and hasattr(main, attribute) and getattr(main, attribute) is not None:
            getattr(main, attribute).discard(name)
            main.refresh_filter_buttons()
        main.refresh_categories()
        main.refresh_list()


def menu(owner, kind, name, point, dropdown=None):
    if not name: return
    # Keep the list visible. Opening a native menu must not run a nested event
    # loop inside the mouse-release handler or dismiss its floating parent.
    panel = dropdown.popup if dropdown is not None else None
    popup = QMenu(panel or owner)
    popup.addAction('删除定义：' + name, lambda: delete_from_widget(owner, kind, name))
    owner._definition_menu = popup
    if panel is not None:
        panel.setProperty('contextMenuOpen', True)
    def finished():
        if panel is not None:
            panel.setProperty('contextMenuOpen', False)
        if getattr(owner, '_definition_menu', None) is popup:
            owner._definition_menu = None
        popup.deleteLater()
    popup.aboutToHide.connect(finished)
    popup.popup(point)


class DefinitionMouseFilter(QObject):
    def __init__(self, combo, owner, kind):
        super().__init__(combo)
        self.combo, self.owner, self.kind = combo, owner, kind

    def eventFilter(self, target, event):
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease) and event.button() == Qt.MouseButton.RightButton:
            if event.type() == QEvent.Type.MouseButtonRelease:
                index = self.combo.view().indexAt(event.position().toPoint())
                if index.isValid():
                    name = self.combo.itemData(index.row())
                    point = event.globalPosition().toPoint()
                    menu(self.owner, self.kind, name, point, dropdown=self.combo)
            return True
        if event.type() == QEvent.Type.ContextMenu:
            return True
        return False


def bind_combo(combo, owner, kind):
    combo.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    combo.customContextMenuRequested.connect(lambda pos: menu(owner, kind, combo.currentData(), combo.mapToGlobal(pos)))
    handler = DefinitionMouseFilter(combo, owner, kind)
    combo._definition_mouse_filter = handler
    combo.view().viewport().installEventFilter(handler)
