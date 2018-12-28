package  {
	import flash.display.DisplayObject;
	import flash.display.InteractiveObject;
	import flash.display.MovieClip;
	import flash.events.Event;
	import flash.events.MouseEvent;
	import flash.text.TextField;
	import flash.text.TextFormat;
	import net.wg.gui.components.controls.ButtonIconNormal;
	import net.wg.gui.components.controls.CheckBox;
	import net.wg.gui.components.controls.DropdownMenu;
	import net.wg.gui.components.controls.InfoIcon;
	import net.wg.gui.components.controls.LabelControl;
	import net.wg.gui.components.controls.RadioButton;
	import net.wg.gui.components.controls.SoundButtonEx;
	import net.wg.gui.components.controls.TextInput;
	import net.wg.infrastructure.base.AbstractWindowView;
	import net.wg.infrastructure.interfaces.IWindow;
	import net.wg.infrastructure.interfaces.IWrapper;
	import scaleform.clik.constants.InvalidationType;
	import scaleform.clik.controls.ButtonGroup;
	import scaleform.clik.core.UIComponent;
	import scaleform.clik.data.DataProvider;
	import scaleform.clik.events.ListEvent;
	import scaleform.gfx.TextFieldEx;

	public class SkinnerUI extends AbstractWindowView {
		private static const SCROLL_ITEM_LIMIT: int = 9;
		private var texts:Object;
		private var settings:Object;
		private var mode:String;
		
		private var skinTypes:Array = ["static", "dynamic"]
		private var teams:Array = ["player", "ally", "enemy"];
		private var skinNameArray:Array = [];
		
		private var headerSize:int = 54;
		
		private var backBtn:SoundButtonEx;
		private var saveBtn:SoundButtonEx;
		
		private var skinTypeDropdown:DropdownMenu;
		private var skinNameDropdown:DropdownMenu;
		private var teamDropdown:DropdownMenu;
		
		private var useForLabel:MovieClip;
		private var useForStatLabel:MovieClip;
		private var useForDynLabel:MovieClip;
		private var useForAllyLabel:MovieClip;
		private var useForEnemyLabel:MovieClip;
		private var useForPlayerLabel:MovieClip;
		private var useForAllyCB:MovieClip;
		private var useForEnemyCB:MovieClip;
		private var useForPlayerCB:MovieClip;
		private var useForAllyCB_dyn:MovieClip;
		private var useForEnemyCB_dyn:MovieClip;
		private var useForPlayerCB_dyn:MovieClip;
		
		private var namesRadioUI:UIComponent;
		private var namesRadioGroup:ButtonGroup;
		private var upBtn:ButtonIconNormal;
		private var downBtn:ButtonIconNormal;
		public var py_printLog:Function;
		public var py_onRequestSettings:Function;
		public var py_checkSettings:Function;
		public var py_onSaveSettings:Function;
		
		public function SkinnerUI() {
			super();
			//this.canDrag = true;
			this.canResize = false;
			this.isCentered = true;
			//this.canClose = true;
		}

		override protected function onPopulate(): void {
			super.onPopulate();
			this.width = 240;
			this.height = 180;
			this.invalidate(InvalidationType.SIZE);
			this.skinsSetupBtnClick(null);
		}

		override public function onTryClosingS(): Boolean {
			this.mode = "closing";
			return this.py_checkSettings(this.settings);
		}

		private function createLabel(text: String, tooltip: String, x: int, y: int): MovieClip {
			var _loc3_: UIComponent = new UIComponent();
			var _loc4_: LabelControl = LabelControl(App.utils.classFactory.getComponent("LabelControl", LabelControl));
			_loc4_.width = 240;
			_loc4_.text = text;
			if (tooltip) {
				_loc4_.toolTip = tooltip;
				_loc4_.infoIcoType = InfoIcon.TYPE_INFO;
			}
			_loc3_.addChild(_loc4_);
			_loc4_.validateNow();
			var lb: MovieClip = new MovieClip();
			lb.addChild(_loc3_);
			lb["label"] = _loc4_;
			lb.y = y;
			lb.x = x;
			this.addChild(lb);
			return lb;
		}

		private function createCheckBox(text: String, tooltip: String, x: int, y: int, width: int, callback: Function): MovieClip {
			var cb: CheckBox = null;
			var checkboxUI: UIComponent = new UIComponent();
			cb = CheckBox(App.utils.classFactory.getComponent("CheckBox", CheckBox));
			cb.label = text;
			cb.selected = false;
			cb.toolTip = tooltip;
			cb.infoIcoType = !! tooltip ? InfoIcon.TYPE_INFO : "";
			cb.width = width;
			cb.invalidateSize();
			cb.invalidateState();
			cb.invalidateData();
			cb.validateNow();
			if (callback != null) {
				cb.addEventListener(Event.SELECT, callback);}
			checkboxUI.addChild(cb);
			var result: MovieClip = new MovieClip();
			result.addChild(checkboxUI);
			result.cb = cb;
			result.x = x;
			result.y = y;
			this.addChild(result);
			return result;
		}
		
		private function applyDropdownLimits(bar:*, counts:int): void {
			var dropdown:DropdownMenu = bar as DropdownMenu;
			if (counts > SCROLL_ITEM_LIMIT) {
				dropdown["componentInspectorSetting"] = true;
				dropdown.scrollBar = "ScrollBar";
				dropdown.rowCount = SCROLL_ITEM_LIMIT;
				dropdown.inspectableThumbOffset = {"top": 0,"bottom": 0};
				dropdown["componentInspectorSetting"] = false;
			} else {
				dropdown.rowCount = counts;
			}
		}
		
		private function createDropdown(x: int, y: int, callback: Function): DropdownMenu {
			var dropdown: DropdownMenu = App.utils.classFactory.getComponent("DropdownMenuUI", DropdownMenu);
			dropdown.itemRenderer = App.utils.classFactory.getClass("DropDownListItemRendererSound");
			dropdown.dropdown = "DropdownMenu_ScrollingList";
			dropdown.menuDirection = "down";
			dropdown.menuMargin = 1;
			//dropdown.menuRowsFixed = false;
			//dropdown.menuWrapping = "normal";
			//dropdown.scrollBar = "";
			dropdown.showEmptyItems = false;
			dropdown.x = x;
			dropdown.y = y;
			dropdown.width = 223;
			dropdown.menuWidth = 224;
			//dropdown.menuRowsFixed = true;
			//dropdown.soundId = "";
			//dropdown.soundType = "dropDownMenu";
			//dropdown.autoSize = "none";
			dropdown.enabled = true;
			dropdown.enableInitCallback = false;
			dropdown.focusable = true;
			dropdown.addEventListener(ListEvent.INDEX_CHANGE, callback, false, 0, true);
			//dropdown["componentInspectorSetting"] = false;
			this.addChild(dropdown);
			dropdown.validateNow();
			return dropdown;
		}

		private function swapByIdx(a: Array, idx1: int, idx2: int): void {
			var tmpElem: * = a[idx1];
			a[idx1] = a[idx2];
			a[idx2] = tmpElem;
		}

		private function changeWindow(header: String, height: int): void {
			App.utils.focusHandler.setFocus(this);
			if (window) {
				window.title = header;
				window.height = this.headerSize + height;
			}
		}

		public function as_updateData(texts: Object, settings: Object): void {
			this.texts = texts;
			this.settings = settings;
			this.skinNameArray = [];
			for (var name: String in this.settings.skins) {
				this.skinNameArray.push(name);
			}
			this.skinNameArray.sort(Array.CASEINSENSITIVE);
		}

		private function addButtons(y: int): void {
			this.backBtn = App.utils.classFactory.getComponent("ButtonNormal", SoundButtonEx);
			this.backBtn.width = 100;
			this.backBtn.height = 23;
			this.backBtn.x = 8;
			this.backBtn.y = y;
			if (this.mode == "skinSetup") {
				var prioritiesRequired:Boolean = false;
				for each (var type:Object in this.settings.priorities) {
					for each (var team:Array in type) {
						prioritiesRequired ||= (team.length > 1);
					}
				}
				this.backBtn.enabled = prioritiesRequired;
				this.backBtn.label = this.texts.skinPriorityBtn;
			} else if (this.mode == "skinPriority") {
				this.backBtn.enabled = true;
				this.backBtn.label = this.texts.skinSetupBtn;
			}
			this.backBtn.addEventListener(MouseEvent.CLICK, this.backBtnClick, false, 0, true);
			this.backBtn.validateNow();
			this.addChild(this.backBtn);
			this.saveBtn = App.utils.classFactory.getComponent("ButtonRed", SoundButtonEx);
			this.saveBtn.width = 100;
			this.saveBtn.height = 23;
			this.saveBtn.x = 128;
			this.saveBtn.y = y;
			this.saveBtn.label = this.texts.saveBtn;
			this.saveBtn.addEventListener(MouseEvent.CLICK, this.saveBtnClick, false, 0, true);
			this.saveBtn.validateNow();
			this.addChild(this.saveBtn);
		}

		private function removeButtons(): void {
			this.backBtn.removeEventListener(MouseEvent.CLICK, this.backBtnClick);
			this.backBtn.dispose();
			this.backBtn = null;
			this.saveBtn.removeEventListener(MouseEvent.CLICK, this.saveBtnClick);
			this.saveBtn.dispose();
			this.saveBtn = null;
		}

		private function skinsSetupBtnClick(param1: Event): void {
			//this.removeMenuButtons();
			this.py_onRequestSettings();
			this.removeChildren();
			this.mode = "skinSetup";
			this.changeWindow(this.texts.skinSetup, 180);
			this.skinNameDropdown = this.createDropdown(8, 8, this.skinNameDropdownChange);
			this.useForLabel = this.createLabel(this.texts.useFor_header_text, "", 8, 38);
			this.useForPlayerLabel = this.createLabel(this.texts.useFor_player_text, "", 8, 78);
			this.useForAllyLabel = this.createLabel(this.texts.useFor_ally_text, "", 8, 98);
			this.useForEnemyLabel = this.createLabel(this.texts.useFor_enemy_text, "", 8, 118);
			this.useForStatLabel = this.createLabel(this.texts.skinType_static.slice(0, 4) + ".", "", 138, 58);
			this.useForDynLabel = this.createLabel(this.texts.skinType_dynamic.slice(0, 3) + ".", "", 188, 58);
			this.useForPlayerCB = this.createCheckBox("", "", 142, 78, 20, this.UFPCBChange);
			this.useForAllyCB = this.createCheckBox("", "", 142, 98, 20, this.UFACBChange);
			this.useForEnemyCB = this.createCheckBox("", "", 142, 118, 20, this.UFECBChange);
			this.useForPlayerCB_dyn = this.createCheckBox("", "", 192, 78, 20, null);
			this.useForAllyCB_dyn = this.createCheckBox("", "", 192, 98, 20, this.UFACBDChange);
			this.useForEnemyCB_dyn = this.createCheckBox("", "", 192, 118, 20, this.UFECBDChange);
			this.addButtons(154);
			var names: Array = new Array();
			var iter: int = 0;
			for each (var name:String in this.skinNameArray) {
				names.push( { label: String(name), data: Number(iter) } );
				iter++;}
			this.applyDropdownLimits(this.skinNameDropdown, names.length);
			//this.skinNameDropdown.rowCount = names.length;
			this.skinNameDropdown.dataProvider = new DataProvider(names);
			if (!this.skinNameDropdown.selectedIndex) {
				this.skinNameDropdownChange(null);}
			this.skinNameDropdown.selectedIndex = 0;
		}

		private function prioritiesBtnClick(param1: Event): void {
			//this.removeMenuButtons();
			this.py_onRequestSettings();
			this.removeChildren();
			this.mode = "skinPriority";
			this.changeWindow(this.texts.skinPriority, 220);
			this.skinTypeDropdown = this.createDropdown(8, 8, this.skinTypeDropdownChange);
			this.teamDropdown = this.createDropdown(8, 38, this.teamDropdownChange);
			this.namesRadioUI = new UIComponent();
			this.namesRadioGroup = ButtonGroup.getGroup("skinPriority", this.namesRadioUI);
			this.namesRadioUI.x = 38;
			this.namesRadioUI.y = 48;
			this.addChild(this.namesRadioUI);
			this.upBtn = App.utils.classFactory.getComponent("ButtonIconNormalUI", ButtonIconNormal);
			this.upBtn.width = 23;
			this.upBtn.height = 23;
			this.upBtn.iconSource = "../maps/icons/messenger/icons/up.png";
			this.upBtn.x = 8;
			this.upBtn.y = 68;
			this.upBtn.addEventListener(MouseEvent.CLICK, this.upBtnClick, false, 0, true);
			this.addChild(this.upBtn);
			this.downBtn = App.utils.classFactory.getComponent("ButtonIconNormalUI", ButtonIconNormal);
			this.downBtn.width = 23;
			this.downBtn.height = 23;
			this.downBtn.iconSource = "../maps/icons/messenger/icons/down.png";
			this.downBtn.x = 8;
			this.downBtn.y = 98;
			this.downBtn.addEventListener(MouseEvent.CLICK, this.downBtnClick, false, 0, true);
			this.addChild(this.downBtn);
			this.addButtons(194);
			var types: Array = new Array();
			var iter: int = 0;
			for each (var skinType:String in this.skinTypes) {
				types.push( { label: this.texts["skinType_" + skinType], data: Number(iter) } );
				iter++;
			}

			this.applyDropdownLimits(this.skinTypeDropdown, types.length);
			//this.skinTypeDropdown.rowCount = types.length;
			this.skinTypeDropdown.dataProvider = new DataProvider(types);
			this.skinTypeDropdown.selectedIndex = 0;
			var teams:Array = new Array();
			var it:int = 0;
			for each(var team:String in this.teams) {
				teams.push( { label: this.texts["team_" + team], data: Number(it) } );
				it++;
			}

			this.applyDropdownLimits(this.teamDropdown, teams.length);
			//this.teamDropdown.rowCount = teams.length;
			this.teamDropdown.dataProvider = new DataProvider(teams);
			if (!this.teamDropdown.selectedIndex) {
				this.teamDropdownChange(null);
			}
			this.teamDropdown.selectedIndex = 0;
		}

		private function skinTypeDropdownChange(param1: Event): void {
			if (this.mode == "skinPriority") {
				this.teamDropdownChange(null);
			}
		}

		private function teamDropdownChange(param1: Event): void {
			if (this.teamDropdown.selectedIndex == -1) {
				return;
			}
			var team: String = this.teams[this.teamDropdown.selectedIndex];
			if (this.mode == "skinPriority") {
				var skinType: String = this.skinTypes[this.skinTypeDropdown.selectedIndex];
				var nameArray:Array = this.settings.priorities[skinType][team];
				while (this.namesRadioUI.numChildren) {
					this.namesRadioGroup.removeButton(this.namesRadioUI.removeChildAt(0) as RadioButton);
				}
				if (nameArray.length) {
					this.downBtn.enabled = true;
					this.upBtn.enabled = true;
					var radioButton:RadioButton = null;
					var i:int = 0;
					while (i < nameArray.length) {
						radioButton = RadioButton(App.utils.classFactory.getComponent("RadioButton", RadioButton));
						radioButton.y = (i + 1) * 20;
						radioButton.label = nameArray[i];
						radioButton.width = 240;
						this.namesRadioUI.addChild(radioButton);
						this.namesRadioGroup.addButton(radioButton);
						radioButton.addEventListener(Event.SELECT, this.namesRadioGroupClick);
						i++;
					}
					if (!this.namesRadioGroup.selectedIndex) {
						this.namesRadioGroupClick(null);
					}
					this.namesRadioGroup.setSelectedButtonByIndex(0);
				} else {
					this.downBtn.enabled = false;
					this.upBtn.enabled = false;
				}
			}
		}

		private function skinNameDropdownChange(param1:Event): void {
			var skinName:String = this.skinNameArray[this.skinNameDropdown.selectedIndex]
			this.useForAllyCB["cb"].enabled = true;
			this.useForEnemyCB["cb"].enabled = true;
			this.useForPlayerCB["cb"].enabled = true;
			this.useForAllyCB["cb"].selected = this.settings.skins[skinName].static.ally;
			this.useForEnemyCB["cb"].selected = this.settings.skins[skinName].static.enemy;
			this.useForPlayerCB["cb"].selected = this.settings.skins[skinName].static.player;
			this.useForAllyCB_dyn["cb"].enabled = true;
			this.useForEnemyCB_dyn["cb"].enabled = true;
			this.useForPlayerCB_dyn["cb"].enabled = false;
			this.useForAllyCB_dyn["cb"].selected = this.settings.skins[skinName].dynamic.ally;
			this.useForEnemyCB_dyn["cb"].selected = this.settings.skins[skinName].dynamic.enemy;
			this.useForPlayerCB_dyn["cb"].selected = false;
		}

		private function namesRadioGroupClick(param1: Event): void {
			var team: String = this.teams[this.teamDropdown.selectedIndex];
			var skinType: String = this.skinTypes[this.skinTypeDropdown.selectedIndex];
			var nameArray:Array = this.settings.priorities[skinType][team];
			var selectedIdx: int = this.namesRadioGroup.selectedIndex;
			this.upBtn.enabled = Boolean(selectedIdx);
			this.downBtn.enabled = Boolean(selectedIdx + 1 != nameArray.length)
		}

		private function upBtnClick(param1: Event): void {
			var team: String = this.teams[this.teamDropdown.selectedIndex];
			var skinType: String = this.skinTypes[this.skinTypeDropdown.selectedIndex];
			var selectedIdx: int = this.namesRadioGroup.selectedIndex;
			this.swapByIdx(this.settings.priorities[skinType][team], selectedIdx, selectedIdx - 1);
			this.teamDropdownChange(null);
			this.namesRadioGroup.setSelectedButtonByIndex(selectedIdx - 1);
		}

		private function downBtnClick(param1: Event): void {
			var team: String = this.teams[this.teamDropdown.selectedIndex];
			var skinType: String = this.skinTypes[this.skinTypeDropdown.selectedIndex];
			var selectedIdx: int = this.namesRadioGroup.selectedIndex;
			this.swapByIdx(this.settings.priorities[skinType][team], selectedIdx, selectedIdx + 1);
			this.teamDropdownChange(null);
			this.namesRadioGroup.setSelectedButtonByIndex(selectedIdx + 1);
		}

		private function backBtnClick(param1: Event): void {
			if (this.py_checkSettings(this.settings)) {
				this.as_onSettingsChecked();
			}
		}
		
		public function as_onSettingsChecked(): void {
			this.removeButtons();
			if (this.mode == "closing") {
				this.onWindowCloseS();
			} else if (this.mode == "skinSetup") {
				this.prioritiesBtnClick(null);
			} else if (this.mode == "skinPriority") {
				this.skinsSetupBtnClick(null);
			}
		}

		private function saveBtnClick(param1: Event): void {
			this.py_onSaveSettings(this.settings);
			this.py_onRequestSettings();
		}

		private function CBChange(type: String, CBType: String, team: String, selected: Boolean): void {
			if (this.mode == "skinSetup") {
				var nameNum:int = this.skinNameDropdown.selectedIndex;
				var name:String = this.skinNameArray[nameNum];
				this.settings.skins[name][type][team] = selected;
				var nameArray:Array = this.settings.priorities[type][team]
				var nameIdx:int = nameArray.indexOf(name)
				if (selected && nameIdx == -1) {
					nameArray.push(name);
				} else if (!selected && nameIdx >= 0) {
					nameArray.splice(nameIdx, 1);
				}
			}
		}

		private function UFPCBChange(param1: Event): void {
			this.CBChange("static", "useFor", "player", this.useForPlayerCB["cb"].selected);
		}

		private function UFACBChange(param1: Event): void {
			this.CBChange("static", "useFor", "ally", this.useForAllyCB["cb"].selected);
		}

		private function UFECBChange(param1: Event): void {
			this.CBChange("static", "useFor", "enemy", this.useForEnemyCB["cb"].selected);
		}

		private function UFACBDChange(param1: Event): void {
			this.CBChange("dynamic", "useFor", "ally", this.useForAllyCB_dyn["cb"].selected);
		}

		private function UFECBDChange(param1: Event): void {
			this.CBChange("dynamic", "useFor", "enemy", this.useForEnemyCB_dyn["cb"].selected);
		}
	}
}
