package polyacov_yury.views.battle {
	import flash.text.TextField;
	import flash.text.TextFormat;
	import flash.text.TextFormatAlign;
	import net.wg.data.constants.InvalidationType;
	import net.wg.data.constants.generated.LAYER_NAMES;
	import net.wg.gui.battle.views.BaseBattlePage;
	import net.wg.gui.components.containers.MainViewContainer;
	import net.wg.infrastructure.base.AbstractView;
	import net.wg.infrastructure.managers.impl.ContainerManagerBase;

	public class BigTextConsumablesPanel extends AbstractView {
		private static const NAME_MAIN:String = "main";
		
		public static var ui:BigTextConsumablesPanel;
		public var py_log:Function;
		
		private var viewPage:BaseBattlePage;
		
		public function BigTextConsumablesPanel() : void {
			super();
			ui = this;
		}
		
		override protected function onPopulate():void {
			super.onPopulate();
			try {
				parent.removeChild(this);
				var viewContainer:MainViewContainer = (App.containerMgr as ContainerManagerBase).getContainer(LAYER_NAMES.LAYER_ORDER.indexOf(LAYER_NAMES.VIEWS)) as MainViewContainer;
				viewContainer.setFocusedView(viewContainer.getTopmostView());
				viewPage = viewContainer.getChildByName(NAME_MAIN) as BaseBattlePage;
				this.invalidateRenderers();
			} catch (error:Error) {
				DebugUtils.LOG_ERROR(error.getStackTrace());
				py_log(error.getStackTrace());
			}
		}

		public function invalidateRenderers(): void {
			try {
				var consumablesPanel:* = viewPage["consumablesPanel"];
				if (consumablesPanel == null) {
					return;
				}
				var tf:TextFormat = new TextFormat("ZurichCond", 24, null, null, null, null, null, null, TextFormatAlign.CENTER);
				for (var i:int = 0; i < consumablesPanel.numChildren; i++) {
					var obj:* = consumablesPanel.getChildAt(i);
					var textField:TextField = obj["quantityField"];
					if (textField != null) {
						textField.defaultTextFormat = tf;
						textField.setTextFormat(tf);
						textField.height = 39.25;
						textField.x = 6.0;
						textField.y = 10.5;
					}
					textField = obj["cooldownTimerTf"];
					if (textField != null) {
						textField.defaultTextFormat = tf;
						textField.setTextFormat(tf);
						textField.height = 39.75;
						textField.x = 3.0;
						textField.y = 10.5;
					}
				}
			} catch (error:Error) {
				DebugUtils.LOG_ERROR(error.getStackTrace());
				py_log(error.getStackTrace());
			}
		}

		override protected function onDispose():void {
			ui = null;
			viewPage = null;
			super.onDispose();
		}
	}
}
