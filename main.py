#!/usr/bin/python

import os
import argparse
from PyQt4 import QtGui,QtCore
from random import sample,random
from qtarotconfig import QTarotConfig
from utilities import ZPGraphicsView,QTarotScene,QTarotItem,QDeckBrowser
from urlparse import urlparse

#http://www.sacred-texts.com/tarot/faq.htm#US1909
"""
Format for Ouija session:
me/entity,date,msg
"""


class QTarot(QtGui.QMainWindow):

	def __init__(self):
		super(QTarot, self).__init__()
		self.initUI()

	def updateCards(self):
		for item in self.scene.items():
			if isinstance(item,QTarotItem):
				item.refresh()
				item.reposition()
		self.scene.invalidate()

	def updateTable(self,fn="skin:table.png"):
		self.scene.table=QtGui.QPixmap(fn)
		for item in self.scene.items():
			if isinstance(item,QTarotItem):
				item.refresh()
				item.reposition()
		self.scene.invalidate()

	def pickTable(self):
		filename=QtGui.QFileDialog.getOpenFileName (self, caption="Open a new file", \
		directory=QtCore.QDir.homePath(), filter="Images (%s)" %(' '.join(formats)))
		if filename > "":
			self.updateTable(fn=filename)

	def saveReadingAsIMG(self,filename,fmt):
		pixMap = QtGui.QPixmap(self.scene.sceneRect().width(),self.scene.sceneRect().height())

		c = QtGui.QColor(0)
		c.setAlpha(0)
		pixMap.fill(c)

		painter=QtGui.QPainter(pixMap)
		self.scene.render(painter)
		painter.end()
		pixMap.save(filename,format=fmt)

	def saveReadingAsHTML(self,filename):
		store_here="{}.files".format(filename.replace(".html",""))
		if not os.path.exists(store_here):
			os.makedirs(store_here)
		reading_px=os.path.join(store_here,"reading.png")
		reading_pxh=os.path.join(os.path.basename(store_here),"reading.png")
		self.saveReadingAsIMG(reading_px,'png')

		f=open(filename,'wb')
		import shutil
		f2=open(os.path.join(os.sys.path[0],'export_read.html'))
		template=f2.read()
		f2.close()

		cards=""
		layout="&lt;Unknown&gt;"
		deck_def_credits=""
		layout_credits=""
		deck=""
		for item in self.scene.items():
			if isinstance(item,QTarotItem):
				if layout == "&lt;Unknown&gt;":
					layout=item.posData.getparent().get('name')
					layout_credits=self.generateCredits(item.posData)
				if not deck_def_credits:
					deck_def_credits=self.generateCredits(item.card)
					deck=item.card.getroottree().getroot().get('name')
				text,copy_from,save_file=self.generateCardText(item.card,\
				item.rev,item.posData.purpose.text,newfp=store_here)
				shutil.copy(copy_from,save_file)
				cards=''.join([cards,text])

		f.write(template.format(cards=cards,deck=deck,\
		layout=layout,reading_px=reading_pxh,layout_credits=layout_credits,\
		deck_def_credits=deck_def_credits))
		f.close()

	def saveReading(self,filename=None):
		if filename <= "":
			filename=str(QtGui.QFileDialog.getSaveFileName(self, caption="Save Current Reading",
				filter="Images (%s);;HTML (*.html)" %(' '.join(formats))))
		if filename > "":
			fmt=filename.split(".",1)[-1]
			if fmt == 'html':
				self.saveReadingAsHTML(filename)
			elif "*."+fmt in formats:
				self.saveReadingAsIMG(filename,fmt)
			else:
				QtGui.QMessageBox.critical(self, "Save Current Reading", \
				"Invalid format ({}) specified for {}!".format(fmt,filename))

	def newReading(self,item=None,neg=None,skin=None,deck=None,ask_for_deck=False):
		neg=qtrcfg.negativity if neg is None else neg

		if ask_for_deck:
			deck,ok = QtGui.QInputDialog.getItem(self, "Generate new reading",
									"Deck definition to use:", \
									qtrcfg.deck_defs.keys(), 0, False)
			if ok and not deck.isEmpty():
				deck=str(deck)
			else:
				return
			skin,ok = QtGui.QInputDialog.getItem(self, "Generate new reading",
									"Skin to use (Deck: {}):".format(deck), \
									qtrcfg.deck_defs[deck]['skins'], 0, False)
			if ok:
				skin=str(skin) if not skin.isEmpty() else qtrcfg.deck_defs[deck]['skins'][0]
			else:
				return
		else:
			deck=qtrcfg.deck_def if deck is None or \
				deck not in qtrcfg.deck_defs.keys() else deck
			skin=qtrcfg.deck_skin if skin is None or \
				skin not in qtrcfg.deck_defs[deck]['skins'] else skin

		qtrcfg.setup_skin(skin)

		if item not in qtrcfg.layouts.keys():
			item,ok = QtGui.QInputDialog.getItem(self, "Generate new reading",
			"Layout to use:", qtrcfg.layouts.keys(), 0, False)
			if ok and not item.isEmpty():
				lay=qtrcfg.layouts[str(item)]
			else:
				return
		else:
			lay=qtrcfg.layouts[str(item)]
		self.scene.clear()
		self.scene.invalidate()

		draws=sample(qtrcfg.deck_defs[deck]['definition'].cards(),len(lay.pos[:]))

		for (card,placement) in zip(draws, lay.pos[:]):
			#rectitem=self.scene.addRect(0,0,1/lay.largetDimension()*self.scene.smallerD,\
			#2/lay.largetDimension()*self.scene.smallerD,\
			#pen=QtGui.QPen(QtGui.QColor("red"),2),\
			#brush=QtGui.QBrush(QtGui.QColor("indigo")))

			rev=(random() <= neg)
			rectitem=self.scene.addTarot(card,placement,rev)
			rectitem.reposition()
			rectitem.emitter.showName.connect(self.statusBar().showMessage)
			rectitem.emitter.clearName.connect(self.statusBar().clearMessage)
			rectitem.emitter.showAllInfo.connect(self.cardInfo)

	def generateCredits(self, card):
		def_data = card.getroottree().getroot()
		authors=[]
		sources=[]
		if def_data.tag == "deck":
			copytype="Deck definition"
		elif def_data.tag == "layout":
			copytype="Layout"
		else:
			copytype="&lt;Unknown&gt;"

		for a in def_data.author[:]:
			if a.text:
				authors.append(a.text)
			else:
				authors.append("&lt;Unknown&gt;")

		for s in def_data.source[:]:
			if s.text:
				if urlparse(s.text).scheme:
					sources.append(("<a href=\"{s.text}\">"
					"{s.text}</a>").format(s=s))
				else:
					sources.append(s.text)
			else:
				sources.append("&lt;Unknown&gt;")

		authors=', '.join(authors)
		sources='<br />\n'.join(sources)
		return ("{copytype} (c) {authors}"
		"<br />Sources consulted:<br />"
		"\n{sources}<br />\n").format(**locals())

	def generateCardText(self, card, reverse=None, purpose=None, newfp=None, skin=''):
		f=open(os.path.join(os.sys.path[0],'card_info_template.html'))
		template=f.read()
		f.close()
		reading_specific=("<br />\n\t\tCurrent status: {status}<br />"
		"\n\t\tPurpose in layout: {purp}") if reverse is not None \
		and purpose is not None else ""
		if newfp:
			oldfn=str(QtCore.QDir("skin:/")\
			.absoluteFilePath(str(card.file.text)))
			fn=os.path.join(os.path.basename(newfp),os.path.basename(oldfn))
			newfn=os.path.join(newfp,os.path.basename(oldfn))
		else:
			fn="skin:{fn}".format(fn=str(card.file.text))
		if skin:
			oldfn=str(QtCore.QDir("skin:/")\
			.absoluteFilePath(str(card.file.text)))
			fn=os.path.join('skins:{skin}'.format(**locals()),os.path.basename(oldfn))
		revtext=card.meaning.reversed.text if card.meaning.reversed.text else "Cannot be reversed"
		result=template.format(fn=fn, name=card.fullname(), \
		n=card.number, suit=card.getparent().get('name'), \
		af=card.getparent().get('affinity'), \
		normal=card.meaning.normal.text, \
		reverse=revtext,
		reading_specific=reading_specific.format(purp=purpose,\
		status="Reversed" if reverse else "Normal"))
		if newfp:
			return result,oldfn,newfn
		else:
			return result

	def cardInfo(self, card, reverse=False, posdata=None, skin=''):
		dialog=QtGui.QDockWidget(self)
		dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose,True)
		deck_def_credits=self.generateCredits(card)

		if posdata is not None:
			layout_credits=self.generateCredits(posdata)
			if skin:
				full_information=self.generateCardText(card,reverse,posdata.purpose.text,skin=skin)
			else:
				full_information=self.generateCardText(card,reverse,posdata.purpose.text)
		else:
			layout_credits=""
			if skin:
				full_information=self.generateCardText(card,skin=skin)
			else:
				full_information=self.generateCardText(card)

		textdisplay=QtGui.QTextBrowser(dialog)
		textdisplay.setReadOnly(True)
		textdisplay.setAcceptRichText(True)
		textdisplay.setText(("{deck_def_credits}"
		"{layout_credits}"
		"{full_information}").format(**locals()))
		textdisplay.setOpenLinks(False)
		textdisplay.anchorClicked.connect(lambda url: QtGui.\
						QDesktopServices.\
						openUrl(QtCore.QUrl(url)))
		dialog.setWindowTitle("Info on {}".format(card.fullname()))
		dialog.setWidget(textdisplay)
		dialog.show()
		self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dialog)

	def viewCardFromDB(self, index, widget):
		item=widget.previewArea.model().itemFromIndex(index)
		card=str(item.data(32).toString())
		skin=str(item.data(33).toString())
		card=widget.currentDeck()['definition'].xpath(card)
		self.cardInfo(card[0],skin=skin)

	def settingsWrite(self):
		self.settingsChange()
		qtrcfg.save_settings()
		self.settings_dialog.close()

	def settingsChange(self):
		qtrcfg.negativity=self.negativity.value()
		reload_deck=False
		if str(self.deck_skin.currentText()) != qtrcfg.deck_skin:
			qtrcfg.deck_skin=str(self.deck_skin.currentText())
			reload_deck=True
		if str(self.deck_def.currentText()) != qtrcfg.deck_def:
			qtrcfg.deck_def=str(self.deck_def.currentText())
			reload_deck=False
			#pop up a message box saying to save reading or something
		qtrcfg.default_layout=str(self.default_layout.currentText())
		qtrcfg.load_deck_defs()
		qtrcfg.load_layouts()
		qtrcfg.load_skins()
		qtrcfg.current_icon_override=str(self.ico_theme.text())
		if reload_deck:
			self.updateCards()

	def settingsReset(self):
		qtrcfg.reset_settings()
		self.updateSettingsWidgets()

	def fillSkinsBox(self, new_def):
		if qtrcfg.deck_defs.has_key(str(new_def)):
			skins_list=qtrcfg.deck_defs[str(new_def)]['skins']
		else:
			skins_list=[]
		self.deck_skin.clear()
		self.deck_skin.addItems(skins_list)
		idx=self.deck_skin.findText(qtrcfg.deck_skin)
		self.deck_skin.setCurrentIndex(idx)

	def browseDecks(self):
		dialog=QtGui.QDockWidget(self)
		dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose,True)
		dialog.setWindowTitle("Browse Decks")
		ddb=QDeckBrowser(deck_source=qtrcfg.deck_defs)
		ddb.previewArea.doubleClicked.connect(lambda idx:self.viewCardFromDB(idx,ddb))
		dialog.setWidget(ddb)
		dialog.show()
		self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dialog)

	def updateSettingsWidgets(self):
		self.default_layout.addItems(qtrcfg.layouts.keys())
		idx=self.default_layout.findText(qtrcfg.default_layout)
		self.default_layout.setCurrentIndex(idx)
		self.negativity.setValue(qtrcfg.negativity)
		#decks=list(QtCore.QDir("skins:/").entryList())
		#decks.remove(".")
		#decks.remove("..")
		self.deck_def.addItems(qtrcfg.deck_defs.keys())
		idx=self.deck_def.findText(qtrcfg.deck_def)
		self.deck_def.setCurrentIndex(idx)
		self.ico_theme.setText(qtrcfg.current_icon_override)

	def settings(self):
		self.settings_dialog=QtGui.QDialog(self)
		self.settings_dialog.setWindowTitle("Settings")
		#print QtGui.QFontDialog.getFont()
		"""
		Idea for added ouija part
		________________________
		| Tarot     |   Ouija  |
		|___________|          |
		|                      |
		| text        | font | |
		|             |color | |
		| words       | conf | |
		| letters     | conf | |
		+----------------------+
		| layout      | conf | |
		| card bar    | nnnn | |
		|______________________|

		Algorithm for creating board:
		  1. Divide it into 25-25-50, 25-50-25, 50-25-25, or 33.3-33.3-33.3
		  2. Using the first section, find the largest divisor for the number of letters
		  3. So we set up a row this many and place letters
		  4. Find the longest word and how much space it'd take up (words.sort());words[-1]
		  5. Fill the board with words using this interval of space
		  6. craft a string io for a ficticious layout and fill it with the needed positions
		  7. feed this info to the cards picked out
		  8. (there may need to be recoding in the graphicsscene calculateoffset and the card object)
		"""
		label=QtGui.QLabel(("Note: These will not take effect"
		" until you make another reading"),self.settings_dialog)
		groupbox=QtGui.QGroupBox("Reading",self.settings_dialog)
		groupbox2=QtGui.QGroupBox("Appearance",self.settings_dialog)
		vbox=QtGui.QVBoxLayout(self.settings_dialog)
		gvbox=QtGui.QGridLayout(groupbox)
		gvbox2=QtGui.QGridLayout(groupbox2)

		self.negativity=QtGui.QDoubleSpinBox(groupbox)
		self.default_layout=QtGui.QComboBox(groupbox)
		self.negativity.setSingleStep(0.1)
		self.negativity.setRange(0,1)

		self.deck_def=QtGui.QComboBox(groupbox2)
		self.deck_def.currentIndexChanged['QString'].connect(self.fillSkinsBox)
		self.deck_skin=QtGui.QComboBox(groupbox2)
		self.ico_theme=QtGui.QLineEdit(groupbox2)
		self.ico_theme.setToolTip(("You should only set this if Qt isn't"
		" detecting your icon theme.\n"
		"Currently detected icon theme: %s\n"
		"Settings will take effect after a restart") \
		% (qtrcfg.sys_icotheme))

		gvbox.addWidget(QtGui.QLabel("Negativity"),0,0)
		gvbox.addWidget(self.negativity,0,1)
		gvbox.addWidget(QtGui.QLabel("Default Layout"),1,0)
		gvbox.addWidget(self.default_layout,1,1)
		gvbox2.addWidget(QtGui.QLabel("Deck Definitions"),0,0)
		gvbox2.addWidget(self.deck_def,0,1)
		gvbox2.addWidget(QtGui.QLabel("Deck Skins"),2,0)
		gvbox2.addWidget(self.deck_skin,2,1)
		gvbox2.addWidget(QtGui.QLabel("Override Icon Theme"),3,0)
		gvbox2.addWidget(self.ico_theme,3,1)

		buttonbox=QtGui.QDialogButtonBox(QtCore.Qt.Horizontal)
		resetbutton=buttonbox.addButton(QtGui.QDialogButtonBox.Reset)
		okbutton=buttonbox.addButton(QtGui.QDialogButtonBox.Ok)
		applybutton=buttonbox.addButton(QtGui.QDialogButtonBox.Apply)
		cancelbutton=buttonbox.addButton(QtGui.QDialogButtonBox.Cancel)

		resetbutton.clicked.connect(self.settingsReset)
		okbutton.clicked.connect(self.settingsWrite)
		applybutton.clicked.connect(self.settingsChange)
		cancelbutton.clicked.connect(self.settings_dialog.close)
		vbox.addWidget(label)
		vbox.addWidget(groupbox)
		vbox.addWidget(groupbox2)

		vbox.addWidget(buttonbox)

		self.updateSettingsWidgets()
		self.settings_dialog.exec_()

	def initUI(self):
		self.setWindowTitle(app.applicationName())
		self.scene=QTarotScene(self)

		self.view=ZPGraphicsView(self.scene,self)

		self.setCentralWidget(self.view)
		self.setDockNestingEnabled(True)

		exitAction = QtGui.QAction(QtGui.QIcon.fromTheme('application-exit'), 'Exit', self)
		exitAction.setShortcut('Ctrl+Q')
		exitAction.setStatusTip('Exit application')
		exitAction.triggered.connect(self.close)

		newLayAction = QtGui.QAction(QtGui.QIcon.fromTheme('document-new'), 'New Reading', self)
		newLayAction.setShortcut('Ctrl+N')
		newLayAction.setStatusTip('Generate a new reading')
		newLayAction.triggered.connect(self.newReading)

		newChooseAction = QtGui.QAction(QtGui.QIcon.fromTheme('document-new'), 'New Reading (Choose Deck)', self)
		newChooseAction.setShortcut('Ctrl+Shift+N')
		newChooseAction.setStatusTip('Generate a new reading using a deck and skin of choice')
		newChooseAction.triggered.connect(lambda: self.newReading(ask_for_deck=True))

		saveAction = QtGui.QAction(QtGui.QIcon.fromTheme('document-save'), 'Save', self)
		saveAction.setShortcut('Ctrl+S')
		saveAction.setStatusTip('Save')
		saveAction.triggered.connect(self.saveReading)

		openAction = QtGui.QAction(QtGui.QIcon.fromTheme('document-open'), 'Change Table', self)
		openAction.setShortcut('Ctrl+O')
		openAction.setStatusTip('Change the table image')
		openAction.triggered.connect(self.pickTable)
		#self.findChildren(QtGui.QDockWidget, QString name = QString())

		settingsAction = QtGui.QAction(QtGui.QIcon.fromTheme('preferences-other'), 'Settings', self)
		settingsAction.setStatusTip('Settings')
		settingsAction.triggered.connect(self.settings)

		browsingAction = QtGui.QAction(QtGui.QIcon.fromTheme('applications-graphics'), 'Browse Decks', self)
		browsingAction.setStatusTip('Browse all deck definitions and deck skins you have')
		browsingAction.triggered.connect(self.browseDecks)

		st=self.statusBar()

		menubar = self.menuBar()
		fileMenu = menubar.addMenu('&File')
		fileMenu.addAction(exitAction)
		fileMenu.addAction(newLayAction)
		fileMenu.addAction(newChooseAction)
		fileMenu.addAction(openAction)
		fileMenu.addAction(saveAction)
		fileMenu.addAction(settingsAction)

		toolbar = self.addToolBar('Exit')
		toolbar.addAction(exitAction)
		toolbar.addAction(newLayAction)
		toolbar.addAction(openAction)
		toolbar.addAction(saveAction)
		toolbar.addAction(settingsAction)
		toolbar.addAction(browsingAction)

		#self.resize(500, 400)
		self.setWindowTitle('QTarot')

def main():
	global formats
	global app
	global qtrcfg

	formats=set(["*."+str(QtCore.QString(i)).lower() for i in \
	QtGui.QImageWriter.supportedImageFormats ()])
	formats=sorted(list(formats),key=str.lower)
	try:
		formats.remove('*.bw')
	except ValueError:
		pass
	try:
		formats.remove('*.rgb')
	except ValueError:
		pass
	try:
		formats.remove('*.rgba')
	except ValueError:
		pass

	app = QtGui.QApplication(os.sys.argv)

	app.setApplicationName(QTarotConfig.APPNAME)
	app.setApplicationVersion(QTarotConfig.APPVERSION)
	app.setWindowIcon(QtGui.QIcon.fromTheme("qtarot"))

	qtrcfg = QTarotConfig()

	parser = argparse.ArgumentParser(prog='qtarot',description="A simple tarot fortune teller")
	parser.add_argument('-l','--layout', help='The layout to use.',default=qtrcfg.default_layout,choices=qtrcfg.layouts.keys())
	parser.add_argument('-t','--table', help='File to use as table',default="skin:table.png")
	parser.add_argument('-n','--negativity', help='How often cards are reversed', default=qtrcfg.negativity,type=float)
	parser.add_argument('-o','--output', help='Save the reading to this file', default=None)
	parser.add_argument('-d','--deck', help='Deck definition to use', default=qtrcfg.deck_def, choices=qtrcfg.deck_defs.keys())
	parser.add_argument('-s','--skin', help='Deck skin to use (valid values depend on deck definition)',default=qtrcfg.deck_skin)
	args = parser.parse_args(os.sys.argv[1:])

	ex = QTarot()
	ex.updateTable(fn=args.table)
	if args.deck != qtrcfg.deck_def or  args.skin != qtrcfg.deck_skin:
		if args.skin not in qtrcfg.deck_defs[args.deck]['skins']:
			print ("Invalid skin \"{}\" for {}!\n"
			"Valid skins: {}").format(args.skin,args.deck,qtrcfg.deck_defs[args.deck]['skins'])
			exit(1)
	ex.newReading(item=args.layout,neg=args.negativity,skin=args.skin,deck=args.deck)

	if args.output > "":
		ex.saveReading(filename=args.output)
		#os.sys.exit(app.exec_())
	else:
		ex.show()
		os.sys.exit(app.exec_())

if __name__ == "__main__":
	main()
