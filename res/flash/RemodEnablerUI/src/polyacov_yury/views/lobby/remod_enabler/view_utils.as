package polyacov_yury.views.lobby.remod_enabler {
	import flash.display.DisplayObject;
	import flash.display.MovieClip;
	import flash.events.Event;
	import flash.events.MouseEvent;
	import flash.events.TimerEvent;
	import flash.text.TextFormat;
	import flash.utils.Timer;
	import net.wg.gui.components.controls.CheckBox;
	import net.wg.gui.components.controls.DropdownMenu;
	import net.wg.gui.components.controls.InfoIcon;
	import net.wg.gui.components.controls.LabelControl;
	import net.wg.gui.components.controls.SoundButtonEx;
	import net.wg.gui.components.controls.TextFieldShort;
	import net.wg.gui.components.controls.TextInput;
	import net.wg.infrastructure.base.AbstractWindowView;
	import scaleform.clik.constants.InvalidationType;
	import scaleform.clik.core.UIComponent;
	import scaleform.clik.events.ListEvent;
	import scaleform.gfx.TextFieldEx;

	public class view_utils {
		private static const SCROLL_ITEM_LIMIT: int = 9;
		private static const heightMargin:int = 54;
		private static const widthMargin:int = 25;

		public static function createButton(label: String, x: int, y: int, handler: Function, width: int = 125, height:int = 23, big:Boolean = false, type: String = "ButtonNormal"): * {
			var button:SoundButtonEx = App.utils.classFactory.getComponent(type, SoundButtonEx);
			button.width = width;
			button.height = height;
			button.x = x;
			button.y = y;
			button.label = label;
			button.enabled = true;
			if (big) {
				button.constraintsDisabled = true;
				var tf: TextFormat = button.textField.getTextFormat();
				tf.size = 28;
				button.textField.setTextFormat(tf);
			}
			button.addEventListener(MouseEvent.CLICK, handler, false, -100, true);
			button.validateNow();
			return button;
		}

		public static function createLabel(text: String, tooltip: String, x: int, y: int): * {
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
			return lb;
		}

		public static function createCheckBox(text: String, tooltip: String, x: int, y: int, callback: Function, width: int = 240): * {
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
			return result;
		}
		
		public static function applyDropdownLimits(bar:*, counts:int): void {
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
		
		public static function createDropdown(x: int, y: int, callback: Function, width:int=223): * {
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
			dropdown.width = width;
			dropdown.menuWidth = width + 1;
			//dropdown.menuRowsFixed = true;
			//dropdown.soundId = "";
			//dropdown.soundType = "dropDownMenu";
			//dropdown.autoSize = "none";
			dropdown.enabled = true;
			dropdown.enableInitCallback = false;
			//dropdown.focusable = true;
			dropdown.addEventListener(ListEvent.INDEX_CHANGE, callback, false, 0, true);
			//dropdown["componentInspectorSetting"] = false;
			dropdown.validateNow();
			return dropdown;
		}

		public static function createTextInput(param1: String = "", param2: String = "", param3: String = "", x: int = 0, y: int = 0, param4: Boolean = false): * {
			var lb: DisplayObject = null;
			var _loc5_: UIComponent = new UIComponent();
			var _loc6_: Number = !! param1 ? Number(16) : Number(0);
			if (param1) {
				lb = view_utils.createLabel(param1, param2, 0, 0);
				_loc5_.addChild(lb);
			}
			var textInput: TextInput = TextInput(App.utils.classFactory.getComponent("TextInput", TextInput));
			TextFieldEx.setNoTranslate(textInput.textField, true);
			textInput.y = _loc6_;
			textInput.width = 273;
			textInput.text = param3;
			textInput.displayAsPassword = param4;
			_loc5_.addChild(textInput);
			var _loc8_: MovieClip = new MovieClip();
			_loc8_.addChild(_loc5_);
			_loc8_.x = x + 8;
			_loc8_.y = y + 8;
			_loc8_["value"] = textInput;
			return _loc8_;
		}

		public static function changeWindow(window:AbstractWindowView, header: String, width:int, height: int): void {
			if (window.window) {
				(window.window.getTitleBtnEx() as TextFieldShort).altToolTip = header;
				if (header.length > 24) header = header.slice(0, 24) + " " + header.slice(24);
				window.window.title = header;
				window.window.height = view_utils.heightMargin + height;
				window.window.width = view_utils.widthMargin + width;
			}
			window.height = height;
			window.width = width;
			window.invalidate(InvalidationType.SIZE);
		}
	}
}