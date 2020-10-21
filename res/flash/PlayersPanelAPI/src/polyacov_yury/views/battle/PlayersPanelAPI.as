package polyacov_yury.views.battle 
{
	import flash.filters.DropShadowFilter;
	import flash.text.TextField;
	import net.wg.data.constants.generated.LAYER_NAMES;
	import net.wg.gui.battle.random.views.BattlePage;
	import net.wg.gui.battle.views.BaseBattlePage;
	import net.wg.gui.components.containers.MainViewContainer;
	import net.wg.infrastructure.base.AbstractView;
	import net.wg.infrastructure.managers.impl.ContainerManagerBase;
	import scaleform.gfx.TextFieldEx;
	
	public class PlayersPanelAPI extends AbstractView
	{
		private static const NAME_MAIN:String = "main";
		
		public static var ui:PlayersPanelAPI;
		
		public var py_log:Function;
		public var py_update:Function;
		
		private var viewPage:BaseBattlePage;
		
		private var configs:Object = {};
		private var textFields:Object = {};
		
		public function PlayersPanelAPI() : void 
		{
			super();
			ui = this;
		}
		
		override protected function onPopulate():void
		{
			super.onPopulate();
			
			try
			{
				parent.removeChild(this);
				var viewContainer:MainViewContainer = (App.containerMgr as ContainerManagerBase).getContainer(LAYER_NAMES.LAYER_ORDER.indexOf(LAYER_NAMES.VIEWS)) as MainViewContainer;
				viewContainer.setFocusedView(viewContainer.getTopmostView());
				viewPage = viewContainer.getChildByName(NAME_MAIN) as BaseBattlePage;
			}
			catch (error:Error)
			{
				py_log(error.getStackTrace());
			}
		}
		
		override protected function onDispose():void
		{
			super.onDispose();
		}
		
		public function as_create(linkage:String, config:Object) : void 
		{
			if (viewPage) createComponent(linkage, config);
		}
		
		public function as_update(linkage:String, data:Object) : void 
		{
			if (viewPage) updateComponent(linkage, data);
		}
		
		public function as_delete(linkage:String) : void 
		{
			if (viewPage) deleteComponent(linkage);
		}
		
		private function createComponent(linkage:String, config:Object) : void 
		{
			configs[linkage] = config;
			textFields[linkage] = {};
		}
		
		private function updateComponent(linkage:String, data:Object) : void 
		{
			try
			{
				if (!textFields[linkage].hasOwnProperty(data['vehicleID']))
				{
					_createTextField(linkage, data);
				}
				
				var textField:TextField = textFields[linkage][data.vehicleID];
				
				if (configs[linkage]['isHtml'])
					textField.htmlText = data.text;
				else
					textField.text = data.text;
			}
			catch (e:Error)
			{
				DebugUtils.LOG_ERROR(e.getStackTrace());
			}
		}
		
		public function deleteComponent(linkage:String) : void 
		{
			delete configs[linkage];
			delete textFields[linkage];
		}
		
		private function _createTextField(linkage:String, data:Object) : void 
		{
			var isRight:Boolean = false;
			var textField:TextField = null;
			var playersPanelHolder:* = null;
			var movieIndex:Number = 0;
			var config:Object = null;
			var shadow:Object = null;
			
			var playersPanel:* = (viewPage as BattlePage).playersPanel;
			
			playersPanelHolder = playersPanel.listLeft.getHolderByVehicleID(data['vehicleID']);
			if(!playersPanelHolder)
			{
				isRight = true;
				playersPanelHolder = playersPanel.listRight.getHolderByVehicleID(data['vehicleID']);
			}
			
			config = configs[linkage][isRight ? "right" : "left"];
			shadow = configs[linkage]["shadow"];
			
			textField = new TextField();
			textField.visible = true
			textField.height = config.height;
			textField.width = config.width;
			textField.autoSize = config.align;
			textField.selectable = false;
			textField.filters = [new DropShadowFilter(shadow.distance, shadow.angle, shadow.color, shadow.alpha, shadow.blurX, shadow.blurY, shadow.strength, shadow.quality)]
			TextFieldEx.setNoTranslate(textField,true);
			
			textField.x = playersPanelHolder._listItem.vehicleIcon.x + config.x;
			textField.y = playersPanelHolder._listItem.vehicleIcon.y + config.y;
			
			movieIndex = playersPanelHolder._listItem.getChildIndex(playersPanelHolder._listItem.vehicleTF) + 1;
			playersPanelHolder._listItem.addChildAt(textField, movieIndex);
			
			textFields[linkage][data.vehicleID] = textField;
		}
	}
}
