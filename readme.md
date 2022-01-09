# Screenshots wizard

This add-on provides a wizard to take screenshots of the entire screen or specific areas such as objects, windows, etc. It is activated by the _print screen_ key which on standard keyboards is usually the first of the group of three to the right of F12. If you prefer to use another, it can be configured in the NVDA preferences, input gestures.

When the wizard is invoked, a virtual rectangle is created around the object with focus and a layer of keyboard commands is activated with the following

### commands

#### Rectangle information

Keys 1 through 7 provide the following information:

* 1: Coordinates of the upper left and lower right corners.
* 2: Rectangle dimensions, width per height.
* 3: The reference object.
* 4: Proportion of the rectangle area occupied by the reference object.
* 5: Indicates if part of the reference object is outside the rectangle.
* 6: Indicates if the rectangle exceeds the limits of the active window in the foreground.
* 7: Proportion of the screen occupied by the rectangle.

The space key reads all this information in a row.

#### Object selection

The reference object is the object on the screen that is delimited by the rectangle at all times. First, this object will be the one with the focus of the system, but another can be selected with the following keys:

* Up arrow: frames the container of the current object.
* F: Frames the object with the focus.
* N: Frames the object in the objects navigator.
* W: Frames the active window.
* M: frames the object under the mouse pointer.
* S: Frames the entire screen.

With down arrow the changes are undone.

#### Rectangle size

The size of the rectangle can be modified using the following keys:

* With shift + arrows the upper left corner is moved:
* shift + up or down arrow moves the top edge,
* shift + left or right arrow movess the left edge.
* With control + arrows  the lower right corner is moved:
* control + up or down arrow moves the bottom edge,
* control + left or right arrow moves the right edge.
* control + shift + up arrow expands the rectangle, moving all four edges outward.
* control + shift + down arrow contracts the rectangle, moving all four edges inward.

The number of pixels for these movements can be changed with the page up and page down keys. Also in preferences.

By resizing the rectangle the reference object may change. It will always try to select the object that is centered, in the foreground and that occupies a larger area within the rectangle. Object changes will be announced when they occur.

#### Capture the image

Enter key captures the image of the screen area delimited by the rectangle, it is saved in a file and  exits.

Escape key  cancels and exits.

### Settings

In NVDA preferences, options, the following settings can be configured:

* The folder where the files will be saved.  The user's documents folder by default.
* The image file format.
* The action after saving (nothing, open the folder or open the file).
* The number of pixels for each movement.