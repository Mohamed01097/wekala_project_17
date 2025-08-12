# Tree Copy Last Line Module

This module automatically copies data from the last line when creating a new line in editable tree views using Tab navigation.

## Features

- Automatically copies field values from the previous line when creating a new line
- Works with Tab navigation in editable tree views
- Handles different field types appropriately
- Skips system fields and readonly fields
- Compatible with Odoo 17

## Installation

1. Copy this module to your custom addons directory
2. Update the module list
3. Install the module from Apps menu

## Usage

1. Open any editable tree view (like invoice lines, sale order lines, etc.)
2. Edit a line with some data
3. Use Tab to navigate to the last editable column
4. Press Tab again to create a new line
5. The new line will automatically be populated with data from the previous line

## Technical Details

The module patches the ListController to override the `addRecord` method and handles data copying for various field types including:
- Text and character fields
- Numeric fields (integer, float, monetary)
- Selection fields
- Boolean fields
- Date and datetime fields
- Many2one relations

System fields like ID, creation/modification dates, and readonly fields are automatically skipped.
