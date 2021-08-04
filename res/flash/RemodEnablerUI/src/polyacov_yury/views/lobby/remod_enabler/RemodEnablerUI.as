package polyacov_yury.views.lobby.remod_enabler {
	import flash.display.InteractiveObject;
	import flash.display.MovieClip;
	import flash.events.Event;
	import flash.events.MouseEvent;
	import net.wg.gui.components.controls.DropdownMenu;
	import net.wg.gui.components.controls.SoundButtonEx;
	import net.wg.infrastructure.base.AbstractWindowView;
	import scaleform.clik.constants.InvalidationType;
	import scaleform.clik.data.DataProvider;
	import scaleform.clik.events.ListEvent;

	public class RemodEnablerUI extends AbstractWindowView {
		private const teams: Array = ["player", "ally", "enemy"];
		
		private var texts:Object;
		private var settings:Object;
		private var cache:Object;
		private var newSettings:Object;
		private var mode:String;
		private var updating:Boolean = false;
		private var currentVehicleName:String;
		
		private var remodSetupBtn:*;
		private var remodCreateBtn:*;
		
		private var backBtn:*;
		private var saveBtn:*;
		
		private var addBtn:*;
		private var removeBtn:*;
		
		private var remodNameArray: Array;
		private var currentRemods: Array;
		
		private var remodNameDropdown:*;
		private var whitelistDropdown:*;
		
		private var useForLabel:*;
		private var useForAllyLabel:*;
		private var useForEnemyLabel:*;
		private var useForPlayerLabel:*;
		private var allyCB:*;
		private var enemyCB:*;
		private var playerCB:*;
		
		private var nameBox:*;
		private var messageBox:*;
		
		public var py_printLog:Function;
		public var py_onRequestSettings:Function;
		public var py_onSaveSettings:Function;
		public var py_showRemod:Function;
		public var py_onCreateRemod:Function;
		public var py_getRemodData:Function;
		public var py_onRequestRemodDelete:Function;
		public var py_checkSettings:Function;
		public var py_sendMessage:Function;
		
		public function RemodEnablerUI() {
			super();
			//this.canDrag = true;
			this.canResize = false;
			this.isCentered = true;
			//this.canClose = true;
		}

		override protected function onPopulate(): void {
			super.onPopulate();
			this.width = 240;
			this.height = 156;
			this.invalidate(InvalidationType.SIZE);
			this.initSimpleMenu();
		}

		override public function onTryClosingS(): Boolean {
			this.mode = "closing";
			return this.py_checkSettings(this.settings, this.cache);
		}

		private function requestSettings(): void {
			var data:Array = this.py_onRequestSettings();
			this.texts = data[0];
			this.settings = data[1];
			this.cache = data[2];
			this.currentVehicleName = data[3];
			this.remodNameArray = [];
			for (var name: String in this.settings) {
				this.remodNameArray.push(name);
			}
			this.remodNameArray.sort(Array.CASEINSENSITIVE);
		}

		public function initSimpleMenu(): void {
			try {
				this.requestSettings();
				this.removeButtons();
				this.removeChildren();
				this.mode = "simple";
				this.remodNameDropdown = this.addChild(view_utils.createDropdown(8, 8, this.remodNameDropdownChange, 273));
				this.useForLabel = this.addChild(view_utils.createLabel(this.texts.useFor_header_text, "", 8, 38));
				this.playerCB = this.addChild(view_utils.createCheckBox(this.texts.useFor_player_text, "", 8, 58, this.UFPCBChange));
				this.allyCB = this.addChild(view_utils.createCheckBox(this.texts.useFor_ally_text, "", 8, 78, this.UFACBChange));
				this.enemyCB = this.addChild(view_utils.createCheckBox(this.texts.useFor_enemy_text, "", 8, 98, this.UFECBChange));
				this.addBtn = this.addChild(view_utils.createButton(this.texts.addBtn, 8, 123, this.addBtnClick));
				this.removeBtn = this.addChild(view_utils.createButton(this.texts.removeBtn, 153, 123, this.removeBtnClick));
				this.addBottomButtons(153);
				this.calculateSimpleMenuData();
			} catch (error: Error) {
				this.py_printLog(error.getStackTrace());
			}
		}

		public function as_onVehicleReloaded(vehicleName: String): void {
			if (this.currentVehicleName != vehicleName) {
				this.currentVehicleName = vehicleName;
				if (this.mode == "simple") {
					this.calculateSimpleMenuData();
				}
			}
		}

		private function calculateSimpleMenuData(): void {
			view_utils.changeWindow(this, this.texts.header_simple + this.currentVehicleName, 290, 183);
			var names:Array = new Array();
			var iter:int = 0;
			this.currentRemods = [];
			for each (var remodName:String in this.remodNameArray) {
				if (this.settings[remodName].whitelist.indexOf(this.currentVehicleName) >= 0) {
					this.currentRemods.push(remodName);
					names.push({label: remodName, data: iter});
					iter++;
				}
			}
			var isEmpty: Boolean = (names.length == 0)
			if (isEmpty) {
				names.push({label: this.texts.notFound, data:0})
			}
			this.remodNameDropdown.enabled = !isEmpty;
			this.addBtn.enabled = !(this.remodNameArray.length == this.currentRemods.length);
			this.removeBtn.enabled = !isEmpty;
			view_utils.applyDropdownLimits(this.remodNameDropdown, names.length);
			this.remodNameDropdown.dataProvider = new DataProvider(names);
			if (!this.remodNameDropdown.selectedIndex) {
				this.remodNameDropdownChange(null);}
			this.remodNameDropdown.selectedIndex = 0;
		}

		public function initMainMenu(): void {
			try {
				this.requestSettings();
				this.removeChildren();
				this.mode = "advanced_menu";
				view_utils.changeWindow(this, this.texts.header_main, 240, 113);
				this.remodSetupBtn = this.addChild(view_utils.createButton(this.texts.remodSetupBtn, 8, 8, this.remodSetupBtnClick, 223, 32, true));
				this.remodCreateBtn = this.addChild(view_utils.createButton(this.texts.remodCreateBtn, 8, 45, this.remodCreateBtnClick, 223, 32, true));
				this.remodSetupBtn.enabled = Boolean(this.remodNameArray.length);
				this.backBtn = this.addChild(view_utils.createButton(this.texts.backBtn, 8, 88, this.backBtnClick, 100));
			} catch (error: Error) {
				this.py_printLog(error.getStackTrace());
			}
		}

		private function addBottomButtons(y: int = 202): void {
			this.backBtn = this.addChild(view_utils.createButton("", 8, y, this.backBtnClick));
			if (this.mode == "simple") {
				this.backBtn.label = this.texts.advancedBtn;
			} else {
				this.backBtn.label = this.texts.backBtn;
			}
			this.saveBtn = this.addChild(view_utils.createButton("", 153, y, this.saveBtnClick, 125, 23, false, "ButtonRed"));
			if (this.mode == "simple_add") {
				this.saveBtn.label = this.texts.addBtn;
			} else {
				this.saveBtn.label = this.texts.saveBtn;
			}
		}

		private function removeButtons(): void {
			this.removeMenuButtons();
			this.removeARButtons();
			this.removeBottomButtons();
		}

		private function removeMenuButtons(): void {
			if (this.remodSetupBtn != null) {
				this.remodSetupBtn.removeEventListener(MouseEvent.CLICK, this.remodSetupBtnClick);
				this.removeChild(this.remodSetupBtn);
				this.remodSetupBtn = null;
			}
			if (this.remodCreateBtn != null) {
				this.remodCreateBtn.removeEventListener(MouseEvent.CLICK, this.remodCreateBtnClick);
				this.removeChild(this.remodCreateBtn);
				this.remodCreateBtn = null;
			}
		}

		private function removeARButtons(): void {
			if (this.addBtn != null) {
				this.addBtn.removeEventListener(MouseEvent.CLICK, this.addBtnClick);
				this.removeChild(this.addBtn);
				this.addBtn = null;
			}
			if (this.removeBtn != null) {
				this.removeBtn.removeEventListener(MouseEvent.CLICK, this.removeBtnClick);
				this.removeChild(this.removeBtn);
				this.removeBtn = null;
			}
		}

		private function removeBottomButtons(): void {
			if (this.backBtn != null) {
				this.backBtn.removeEventListener(MouseEvent.CLICK, this.backBtnClick);
				this.removeChild(this.backBtn);
				this.backBtn = null;
			}
			if (this.saveBtn != null) {
				this.saveBtn.removeEventListener(MouseEvent.CLICK, this.saveBtnClick);
				this.removeChild(this.saveBtn);
				this.saveBtn = null;
			}
		}

		private function remodSetupBtnClick(param1: Event): void {
			try {
				this.removeButtons();
				this.removeChildren();
				this.mode = "advanced_setup";
				view_utils.changeWindow(this, this.texts.header_setup, 290, 178);
				this.remodNameDropdown = this.addChild(view_utils.createDropdown(8, 8, this.remodNameDropdownChange, 273));
				this.useForLabel = this.addChild(view_utils.createLabel(this.texts.useFor_header_text, "",  9, 37));
				this.playerCB = this.addChild(view_utils.createCheckBox(this.texts.useFor_player_text, "", 8, 57, this.UFPCBChange));
				this.allyCB = this.addChild(view_utils.createCheckBox(this.texts.useFor_ally_text, "", 8, 77, this.UFACBChange));
				this.enemyCB = this.addChild(view_utils.createCheckBox(this.texts.useFor_enemy_text, "", 8, 97, this.UFECBChange));
				this.addBtn = this.addChild(view_utils.createButton(this.texts.addBtn, 184, 120, this.addBtnClick, 95));
				this.whitelistDropdown = this.addChild(view_utils.createDropdown(8, 118, this.whitelistDropdownChange, 172));
				this.whitelistDropdown.validateNow();
				this.addBottomButtons(153);
				var names:Array = [];
				var iter:int = 0;
				for each (var remodName:String in this.remodNameArray) {
					names.push({label: remodName, data: iter});
					iter++;
				}

				view_utils.applyDropdownLimits(this.remodNameDropdown, names.length);
				this.remodNameDropdown.dataProvider = new DataProvider(names);
				if (!this.remodNameDropdown.selectedIndex) {
					this.remodNameDropdownChange(null);
				}
				this.remodNameDropdown.selectedIndex = 0;
			} catch (err: Error) {
				this.py_printLog(err.getStackTrace());
			}
		}

		private function remodCreateBtnClick(param1: Event): void {
			this.removeButtons();
			this.removeChildren();
			this.mode = "advanced_create";
			view_utils.changeWindow(this, this.texts.header_create, 290, 228);
			this.newSettings = this.py_getRemodData();
			this.nameBox = this.addChild(view_utils.createTextInput(this.texts.remodCreate_name_text, "{HEADER}" + this.texts.remodCreate_name_text + "{/HEADER}{BODY}" + this.texts.remodCreate_name_tooltip + "{/BODY}", this.newSettings.name, 0, -2));
			this.nameBox["value"].addEventListener(Event.CHANGE, this.onInputChange);
			this.messageBox = this.addChild(view_utils.createTextInput(this.texts.remodCreate_message_text, "{HEADER}" + this.texts.remodCreate_message_text + "{/HEADER}{BODY}" + this.texts.remodCreate_message_tooltip + "{/BODY}", this.newSettings.message, 0, 40));
			this.messageBox["value"].addEventListener(Event.CHANGE, this.onInputChange);
			this.useForLabel = this.addChild(view_utils.createLabel(this.texts.useFor_header_text, "",  8, 88));
			this.playerCB = this.addChild(view_utils.createCheckBox(this.texts.useFor_player_text, "", 8, 108, this.UFPCBChange));
			this.playerCB.cb.selected = this.newSettings.player;
			this.allyCB = this.addChild(view_utils.createCheckBox(this.texts.useFor_ally_text, "", 8, 128, this.UFACBChange));
			this.allyCB.cb.selected = this.newSettings.ally;
			this.enemyCB = this.addChild(view_utils.createCheckBox(this.texts.useFor_enemy_text, "", 8, 148, this.UFECBChange));
			this.enemyCB.cb.selected = this.newSettings.enemy;
			this.addBtn = this.addChild(view_utils.createButton(this.texts.addBtn, 184, 168, this.addBtnClick, 95));
			this.whitelistDropdown = this.addChild(view_utils.createDropdown(8, 166, this.whitelistDropdownChange, 172));
			this.whitelistDropdown.validateNow();
			this.addBottomButtons(198);
			this.provideWhitelistData();
		}

		public function as_setHighlight(param1: int): void {
			this.nameBox["value"].highlight = Boolean(param1 & 1);
			this.messageBox["value"].highlight = Boolean(param1 & 2);
		}

		private function remodNameDropdownChange(param1: Event): void {
			var name: String;
			if (this.mode == "simple" || this.mode == "simple_add") {
				name = this.currentRemods[this.remodNameDropdown.selectedIndex];
				this.py_showRemod(name);
				this.updating = true;
				for each (var team: String in this.teams) {
					this[team + "CB"].cb.selected = this.remodNameDropdown.enabled && Boolean(this.cache[team][this.currentVehicleName] == name);
					this[team + "CB"].cb.enabled = this.remodNameDropdown.enabled && ((!Boolean(this.cache[team][this.currentVehicleName])) || this[team + "CB"].cb.selected);
				}
				this.updating = false;
			} else if (this.mode == "advanced_setup") {
				name = this.remodNameArray[this.remodNameDropdown.selectedIndex];
				this.py_showRemod(name);
				this.allyCB.cb.selected = this.settings[name].ally;
				this.enemyCB.cb.selected = this.settings[name].enemy;
				this.playerCB.cb.selected = this.settings[name].player;
				this.provideWhitelistData();
			}
		}

		private function provideWhitelistData(): void {
			var WLArray: Array = [];
			if (this.mode == "advanced_setup") {
				WLArray = this.settings[this.remodNameArray[this.remodNameDropdown.selectedIndex]].whitelist;
			} else {
				WLArray = this.newSettings.whitelist;
			}
			var names:Array = [];
			var iter:int = 1;
			names.push({label: this.texts.whiteDropdown_default, data: 0});
			for each (var name:String in WLArray) {
				names.push({label: name, data: iter});
				iter++;}
			view_utils.applyDropdownLimits(this.whitelistDropdown, names.length);
			this.whitelistDropdown.dataProvider = new DataProvider(names);
			this.whitelistDropdown.selectedIndex = 0;
			this.whitelistDropdown.addEventListener(ListEvent.INDEX_CHANGE, this.whitelistDropdownChange, false, 0, true);
		}

		private function addBtnClick(param1: Event): void {
			if (this.mode == "simple") {
				this.mode = "simple_add";
				this.removeARButtons();
				this.removeBottomButtons();
				this.remodNameDropdown.enabled = false;
				this.remodNameDropdownChange(null);
				this.whitelistDropdown = this.addChild(view_utils.createDropdown(8, 123, this.whitelistDropdownChange, 273));
				this.addBottomButtons(153);
				
				var names:Array = [];
				var iter:int = 0;
				this.currentRemods = [];
				for each (var remodName:String in this.remodNameArray) {
					if (this.settings[remodName].whitelist.indexOf(this.currentVehicleName) == -1) {
						if (iter == 0) {
							names.push({label: this.texts.whiteDropdown_default, data: iter});
							iter++;
						}
						this.currentRemods.push(remodName);
						names.push({label: remodName, data: iter});
						iter++;
					}
				}
				var isEmpty: Boolean = (names.length == 0)
				if (isEmpty) {
					names.push({label: this.texts.notFound, data:0})
				}
				this.whitelistDropdown.enabled = !isEmpty;
				this.saveBtn.enabled = false;
				view_utils.applyDropdownLimits(this.whitelistDropdown, names.length);
				this.whitelistDropdown.dataProvider = new DataProvider(names);
				if (!this.whitelistDropdown.selectedIndex) {
					this.whitelistDropdownChange(null);}
				this.whitelistDropdown.selectedIndex = 0;
				return;
			}
			var tankName: String = this.currentVehicleName;
			var nameArray: Array;
			var remod:String;
			if (this.mode == "advanced_setup") {
				remod = this.remodNameArray[this.remodNameDropdown.selectedIndex];
				nameArray = this.settings[remod].whitelist;
			} else {
				remod = this.nameBox.value.text;
				nameArray = this.newSettings.whitelist;
			}
			if (!tankName.length) {
				this.py_sendMessage(tankName, remod, "vehicleAdd", "notSupported");
			} else {
				var nameIdx:int = nameArray.indexOf(tankName);
				if (nameIdx != -1) {
					this.py_sendMessage(tankName, remod, "vehicleAdd", "dupe");
				} else {
					this.py_sendMessage(tankName, remod, "vehicleAdd", "success");
					nameArray.push(tankName);
					this.provideWhitelistData();
				}
			}
		}

		private function whitelistDropdownChange(param1: Event): void {
			if (this.mode == "simple_add") {
				this.saveBtn.enabled = Boolean(this.whitelistDropdown.selectedIndex != 0);
				if (this.whitelistDropdown.selectedIndex != 0) {
					this.py_showRemod(this.currentRemods[this.whitelistDropdown.selectedIndex - 1]);
				}
			} else {
				if (this.whitelistDropdown.selectedIndex == 0) {
					return;
				}
				var remodName:String = ""
				var WLArray: Array = [];
				if (this.mode == "advanced_setup") {
					remodName = this.remodNameArray[this.remodNameDropdown.selectedIndex];
					WLArray = this.settings[remodName].whitelist;
				} else {
					remodName = this.newSettings.name;
					WLArray = this.newSettings.whitelist;
				}
				this.py_onRequestRemodDelete(WLArray[this.whitelistDropdown.selectedIndex - 1], remodName);
			}
		}

		private function onInputChange(param1: Event): void {
			var value: InteractiveObject = param1.target as InteractiveObject;
			try {
				var mode:int = 0;
				if (value == this.nameBox["value"] || value == this.messageBox["value"]) {
					if (!this.nameBox["value"].text) {
						mode += 1;
					}
					if (value == this.nameBox["value"]) {
						this.newSettings.name = this.nameBox["value"].text;
					} else {
						this.newSettings.message = this.messageBox["value"].text;
					}
					this.as_setHighlight(mode);
				}
			} catch (error: Error) {
				this.py_printLog(String(error.getStackTrace()));
			}
		}

		private function backBtnClick(param1: Event): void {
			if (this.mode == "simple_add") {
				this.mode = "simple";
				this.whitelistDropdown.removeEventListener(ListEvent.INDEX_CHANGE, this.whitelistDropdownChange);
				this.removeChild(this.whitelistDropdown);
				this.whitelistDropdown = null;
				this.addBtn = this.addChild(view_utils.createButton(this.texts.addBtn, 8, 123, this.addBtnClick));
				this.removeBtn = this.addChild(view_utils.createButton(this.texts.removeBtn, 153, 123, this.removeBtnClick));
				this.removeBottomButtons();
				this.addBottomButtons(153);
				this.calculateSimpleMenuData();
			} else if (this.mode != "advanced_menu") {
				if (this.py_checkSettings(this.settings, this.cache)) {
					this.as_onSettingsChecked();
				}
			} else {
				this.initSimpleMenu();
			}
		}

		public function as_onSettingsChecked(): void {
			this.removeMenuButtons();
			this.removeBottomButtons();
			if (this.mode == "closing") {
				this.onWindowCloseS();
			} else {
				this.py_showRemod(null);
				this.removeBottomButtons();
				this.initMainMenu();
			}
		}
		
		private function saveBtnClick(param1: Event): void {
			if (this.mode == "simple_add") {
				var remodName:String = this.currentRemods[this.whitelistDropdown.selectedIndex - 1];
				this.py_sendMessage(this.currentVehicleName, remodName, "remodAdd", "success");
				this.settings[remodName].whitelist.push(this.currentVehicleName);
				for each (var team: String in this.teams) {
					if (this.settings[remodName][team] && !Boolean(this.cache[team][this.currentVehicleName])) {
						this.cache[team][this.currentVehicleName] = remodName;
					} else if (this.cache[team][this.currentVehicleName] == null) {
						this.cache[team][this.currentVehicleName] = "";
					}
				}
				this.backBtnClick(null);
			} else if (this.mode == "advanced_create") {
				this.py_onCreateRemod(this.newSettings);
				this.requestSettings();
			} else {
				this.py_onSaveSettings(this.settings, this.cache);
			}
		}

		private function CBChange(team: String, selected: Boolean, enabled: Boolean): void {
			if (this.mode == "simple") {
				if (!this.updating) {
					if (selected) {
						this.cache[team][this.currentVehicleName] = this.currentRemods[this.remodNameDropdown.selectedIndex];
					} else {
						this.cache[team][this.currentVehicleName] = ""; }
				}
			} else if (this.mode == "advanced_setup") {
				var remod:String = this.remodNameArray[this.remodNameDropdown.selectedIndex];
				this.settings[remod][team] = selected;
			} else if (this.mode == "advanced_create") {
				this.newSettings[team] = selected;
			}
		}

		private function removeBtnClick(param1: Event): void {
			if (this.mode == "simple") {
				this.py_onRequestRemodDelete(this.currentVehicleName, this.currentRemods[this.remodNameDropdown.selectedIndex])
			}
		}

		public function as_onRemodDeleteConfirmed(vehicleName: String, remodName: String, proceed: Boolean): void {
			var team: String;
			if (this.mode == "simple") {
				if (!proceed) return;
				var backupVehicle: String = this.currentVehicleName;
				this.currentVehicleName = vehicleName;
				this.calculateSimpleMenuData();
				if (this.currentRemods.indexOf(remodName) != -1) {
					this.currentRemods.splice(this.currentRemods.indexOf(remodName), 1);
				}
				var whitelist: Array = this.settings[remodName].whitelist
				if (whitelist.indexOf(this.currentVehicleName) != -1) {
					whitelist.splice(whitelist.indexOf(this.currentVehicleName), 1);
				}
				for each (team in this.teams) {
					if (!Boolean(this.currentRemods.length)) {
						delete(this.cache[team][this.currentVehicleName]);
					} else if (this.cache[team][this.currentVehicleName] == remodName) {
						this.cache[team][this.currentVehicleName] = "";
					}
				}
				this.currentVehicleName = backupVehicle;
				this.calculateSimpleMenuData();
				return;
			}
			if (proceed) {
				var name:String;
				var nameArray:Array;
				if (this.mode == "advanced_setup") {
					name = this.remodNameArray[this.remodNameDropdown.selectedIndex];
					nameArray = this.settings[name].whitelist;
				} else {
					name = this.nameBox.value.text;
					nameArray = this.newSettings.whitelist;
				}
				var vehIdx:int = this.whitelistDropdown.selectedIndex;
				if (vehIdx != 0) {
					if (this.mode == "advanced_setup") {
						var compatibleRemods: Array = [];
						for each (var remodName:String in this.remodNameArray) {
							if (this.settings[remodName].whitelist.indexOf(nameArray[vehIdx - 1]) >= 0) {
								compatibleRemods.push(remodName);
							}
						}
						for each (team in this.teams) {
							if (this.cache[team][nameArray[vehIdx - 1]] != name) continue;
							if (Boolean(compatibleRemods.length)) {
								this.cache[team][nameArray[vehIdx - 1]] = "";
							} else {
								delete(this.cache[team][nameArray[vehIdx - 1]]);
							}
						}
					}
					this.py_sendMessage(nameArray[vehIdx - 1], name, "vehicleDelete", "success");
					nameArray.splice(vehIdx - 1, 1);
				}
			}
			this.whitelistDropdown.selectedIndex = 0;
			this.provideWhitelistData();
		}

		private function UFPCBChange(param1: Event): void {
			this.CBChange("player", this.playerCB["cb"].selected, this.playerCB["cb"].enabled);
		}

		private function UFACBChange(param1: Event): void {
			this.CBChange("ally", this.allyCB["cb"].selected, this.allyCB["cb"].enabled);
		}

		private function UFECBChange(param1: Event): void {
			this.CBChange("enemy", this.enemyCB["cb"].selected, this.enemyCB["cb"].enabled);
		}
	}
}
