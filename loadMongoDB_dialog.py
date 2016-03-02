# -*- coding: utf-8 -*-
"""
/*!
 * MongoDB to QGIS Loader
 *
 * GUI/ Layer Loader
 * @author Adrian Aksan <adrian.aksan@gmail.com>
 * @created 15/09/2014
 */
"""

import os, sys
from PyQt4.Qt import *
from PyQt4 import QtGui, uic
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ui_loadMongoDB_dialog_base import Ui_loadMongoDBDialogBase
from qgis.core import *
import qgis.utils
from PyQt4.QtCore import QVariant
from django.utils.encoding import smart_str, smart_unicode

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'loadMongoDB_dialog_base.ui'))


# test requirements
try:
    from pymongo import MongoClient

except ImportError as e:
    QMessageBox.critical(iface.mainWindow(),
                         "Missing module",
                         "Pymongo module is required",
                         QMessageBox.Ok)

# test requirements
try:
    import ast

except ImportError as e:
    QMessageBox.critical(iface.mainWindow(),
                         "Missing module",
                         "Ast module is required",
                         QMessageBox.Ok)

# test requirements
try:
    import json

except ImportError as e:
    QMessageBox.critical(iface.mainWindow(),
                         "Missing module",
                         "Json module is required",
                         QMessageBox.Ok)


class loadMongoDBDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):

        """Constructor."""
        super(loadMongoDBDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        QtGui.QDialog.__init__(self, parent, Qt.WindowMinimizeButtonHint)

        self.ui = Ui_loadMongoDBDialogBase()
        self.ui.setupUi(self)

        # sets the progress bar to 0
        self.step = 0
        self.ui.progressBar.setValue(self.step)

        # GUI a single click interface loads the on_click_load function
        self.ui.listCol.itemClicked.connect(self.select_item)

        # Allows the user to select which attribute they would like to see distinct values for
        self.ui.view_all.itemClicked.connect(self.row_select)

        self.ui.load_collection.setEnabled(False)


    def view_all_attributes(self):

        # reset the list count and clear the list
        count = 0
        self.ui.view_all.setEnabled(True)
        self.ui.view_all.clear()

        data = self.collection.find_one()

        for key in data.keys():

            attribute = QListWidgetItem(key)
            self.ui.view_all.insertItem(count, attribute)

            count+=1


    def row_select(self, item):

        self.ui.distinct_button.setEnabled(True)
        self.selected_attribute = item.text()


    def view_distinct(self):

        count = 0
        self.ui.view_distinct.setEnabled(True)
        self.ui.view_distinct.clear()

        self.list_distinct = self.collection.distinct(self.selected_attribute)

        # allows loading of non-string types
        if len(self.list_distinct) != 0:
            self.data_type = type(self.list_distinct)

        # converts all attributes to str types
        self.list_distinct = map(str, self.list_distinct)

        # limit the number of distinct values we get to see
        if len(self.list_distinct) > 20:
            return

        for key in self.list_distinct:

            attribute = QListWidgetItem(str(key))
            self.ui.view_distinct.insertItem(count, attribute)

            count+=1

        self.ui.set_button.setEnabled(True)


    def set_attribute(self):

        self.ui.load_field.clear()
        self.ui.load_field.addItems(list(set(self.list_distinct)))
        self.key = self.selected_attribute
        self.ui.checkBox.setCheckable(True)


    # this is a GUI function for displaying all collections/ details found in the DB
    def show_mdb_collection(self, db_name, server_name, geom_name):

        # reset the list count and clear the list
        count = 0
        self.ui.listCol.clear()
	self.geom_name = geom_name

        try:
            # establish a link to the mongoDB server
            self.client = MongoClient(str(server_name), 27017, serverSelectionTimeoutMS=500)
        except:
            QMessageBox.about(self, "Warning!", "Please select a server to connect to.")
            return

        # db name passed on from the user's input
        self.db = self.client[db_name]

        try:
            # create the list of available collections
            self.collection_list = self.db.collection_names(include_system_collections=False)
        except:
            QMessageBox.about(self, "Warning!", "Server might be offline. Check server and try again.")

            self.reset_all()
            return

        # define the number of columns in our tree widget
        self.ui.listCol.setColumnCount(3)

        if len(self.collection_list) == 0:
            return False

        # search through the list of available collections for collections with geometry
        for x in self.collection_list:

            self.data = self.db[x].find_one()
            num_items = self.db[x].count()

            try:
                if self.data[geom_name]:
                    geom_type = self.data[geom_name]['type']

                else:
                    geom_type = False

            except:
                geom_type = False

            # details of each collection
            details = QTreeWidgetItem([str(x), str(geom_type), str(num_items)])

            # only display the collections with geometry
            if geom_type != False:

                self.ui.listCol.insertTopLevelItem(count, details)
                count += 1

            else:
                pass

        self.client.close()

        return True

    def reset_all(self):

        self.ui.distinct_button.setEnabled(False)
        self.ui.set_button.setEnabled(False)
        self.ui.view_distinct.setEnabled(False)
        self.ui.view_all.setEnabled(False)
        self.ui.load_field.clear()
        self.ui.checkBox.setCheckable(0)


    def select_item(self, item, column):

        self.reset_all()

        # the name of the collection we will be using
        self.collection_name = str(item.text(0))
        # the geometry of the collection
        self.geometry_name = str(item.text(1))
        # divide the collection count to percentages for the progress bar
        self.percent = 100/float(item.text(2))
        self.total = int(item.text(2))

        # load the selected collection into a list
        self.collection = self.db[self.collection_name]

        # enables the load button when an item is selected from the list
        self.ui.load_collection.setEnabled(True)
        self.ui.view_button.setEnabled(True)


    def on_click_load(self):

        # default value of the progress bar is set to 0
        self.counter = 1
        self.ui.progressBar.setValue(self.counter)
        self.ui.progressBar.setMinimum(1)
        self.ui.progressBar.setMaximum(self.total)

        # check if the user wants to limit the selection by distinct value
        if self.ui.checkBox.isChecked():

            load_key = self.ui.load_field.currentText()

            # if the data type is not a string
            if self.data_type != str:
                load_key = ast.literal_eval(load_key)

            self.ourList = self.collection.find({self.key: load_key})

        else:
            self.ourList = self.collection.find()

        # get the first level of attributes, we can modify which fields we want to use
        self.single_return = self.collection.find_one({}, {'geom':0})
        #{} , {"geom": 1}
        self.keys = self.single_return.keys()

        self.attributes = []

        for key in self.keys:
            if (type(self.single_return[key]) is dict):
                continue
            if (type(self.single_return[key]) is list):
                dtype = QVariant.StringList
            if (type(self.single_return[key]) is int):
                dtype = QVariant.Int
            elif (type(self.single_return[key]) is float):
                dtype = QVariant.Double
            else:
                dtype = QVariant.String

            # define the attribute dictionnary
            # add a dictionary of attribute name and type
            self.attributes.append({"name": str(key), "dtype": dtype, "value": key})


        # define the dataLayer type as either Point, LineString or Polygon
        self.dataLayer = QgsVectorLayer(self.geometry_name + '?crs=EPSG:4326', self.collection_name, "memory")

        # prepare the layer for the data we will be inputing
        self.dataLayer.startEditing()
        self.layerData = self.dataLayer.dataProvider()

        # create the attributes based on existing mongoDB field
        # setup the type of each field
        # for attribute in (self.attr_list_new):
        for attr in (self.attributes):
            self.layerData.addAttributes([ QgsField(attr["name"], attr["dtype"])])

        # our attribute container
        self.feature = QgsFeature()
        self.feature.initAttributes(len(self.attributes))

        for value in self.ourList:

            # if the user has selected a collection with point geometry

            geom = value[self.geom_name]

            if geom["type"] == "Point":

                x_coord = geom["coordinates"][0]
                y_coord = geom["coordinates"][1]

                self.populate_attributes(value)

                self.feature.setGeometry(QgsGeometry.fromPoint(QgsPoint(x_coord, y_coord)))
                (res, outFeats) = self.dataLayer.dataProvider().addFeatures([self.feature])

                self.ui.load_collection.setEnabled(False)
                self.ui.listCol.setEnabled(False)


            if geom["type"] == "LineString":

                # used to store a list of poly lines
                line_string = []

                # checks the geometry and only imports valid geometry
                if self.check_valid_geom(value):

                    for y in range(len(geom["coordinates"])):

                        # do not use unless needed, in case there is a multiLineString Object in the DB
                        """
                        if value["geometry"]["type"] != "LineString":
                            pass

                        else:
                        """

                        try:
                            line_string.append(QgsPoint(geom["coordinates"][y][0], geom["coordinates"][y][1]))
                        except:
                            print "error on %s: %s" %(str(value["_id"]), str(sys.exc_info()[0]))

                    self.populate_attributes(value)
                    self.feature.setGeometry(QgsGeometry.fromPolyline(line_string))
                    (res, outFeats) = self.dataLayer.dataProvider().addFeatures([self.feature])
                    del line_string[:]

                self.ui.load_collection.setEnabled(False)
                self.ui.listCol.setEnabled(False)


            # this deals with Polygon geometry
            if geom["type"] == "Polygon":

                # store the polygon points
                poly_shape = []
                # store the line (a poly has multiple lines)
                line_string = []

                # checks the geometry and only imports valid geometry
                if self.check_valid_geom(value):

                    for y in range(len(geom["coordinates"][0])):
                        try:
                            line_string.append(QgsPoint(geom["coordinates"][0][y][0], geom["coordinates"][0][y][1]))
                        except:
                            print "error on %s: %s" %(str(value["_id"]), str(sys.exc_info()[0]))

                    poly_shape.append(line_string);

                    self.populate_attributes(value)
                    try:
                        ps = QgsGeometry.fromPolygon(poly_shape)
                        self.feature.setGeometry(ps)
                    except:
                        print "error on %s: %s" %(str(value["_id"]), str(sys.exc_info()[0]))

                    (res, outFeats) = self.dataLayer.dataProvider().addFeatures([self.feature])
                    del line_string[:]
                    del poly_shape[:]

                    self.ui.load_collection.setEnabled(False)
                    self.ui.listCol.setEnabled(False)

            # this deals with Polygon geometry
            if geom["type"] == "MultiPolygon":

                # store the polygon points
                poly_shape = []
                # store the line (a poly has multiple lines)
                line_string = []

                # checks the geometry and only imports valid geometry
                if self.check_valid_geom(value):

                    for polys in range(len(geom["coordinates"])):
                        for y in range(len(geom["coordinates"][polys])):
                            try:
                                line_string.append(QgsPoint(geom["coordinates"][polys][y][0], geom["coordinates"][polys][y][1]))
                            except:
                                print "error on %s: %s" %(str(value["_id"]), str(sys.exc_info()[0]))
                        poly_shape.append(line_string);

                    self.populate_attributes(value)
                    try:
                        ps = QgsGeometry.fromPolygon(poly_shape)
                        self.feature.setGeometry(ps)
                    except:
                        print "error on %s: %s" %(str(value["_id"]), str(sys.exc_info()[0]))

                    (res, outFeats) = self.dataLayer.dataProvider().addFeatures([self.feature])
                    del line_string[:]
                    del poly_shape[:]

                    self.ui.load_collection.setEnabled(False)
                    self.ui.listCol.setEnabled(False)

            # update the progress bar
            self.event_progress()

            self.ui.listCol.setEnabled(True)

        # commits the changes made to the layer and adds the layer to the map
        self.dataLayer.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayer(self.dataLayer)

    # check for valid geometry
    def check_valid_geom(self, value):

        if value.has_key(self.geom_name):

            if value[self.geom_name].has_key("type"):

                if value[self.geom_name].has_key("coordinates"):

                    if len(value[self.geom_name]["coordinates"]) != 0:

                        return True

                return False

            return False

        return False


    def event_progress(self):

        # convert to an integer for the progress bar
        # self.counter = self.counter + self.percent
        # self.step = int(self.counter) +1

        self.step = self.ui.progressBar.value() + 1

        # set the updated values in the progress bar and process the event
        self.ui.progressBar.setValue(self.step)
        QApplication.processEvents()

        # once the upload has finished, reset the progress back to 0
        # if self.step >= 100:
        if self.step >= self.total:
            self.ui.progressBar.setValue(0)


    # populate keys and sub-keys
    def populate_attributes(self, value):

        index_pos = 0

        for attr in self.attributes:

            try:
                self.feature[index_pos] = value[attr["name"]]
            except:
                self.feature[index_pos] = None

            index_pos += 1
