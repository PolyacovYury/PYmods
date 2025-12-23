package polyacov_yury.views.lobby {
	import flash.events.Event;
	import flash.geom.Rectangle;
	import net.wg.data.constants.generated.LAYER_NAMES;
	import net.wg.gui.components.containers.MainViewContainer;
	import net.wg.gui.lobby.LobbyPage;
	import net.wg.infrastructure.base.AbstractView;
	import net.wg.infrastructure.managers.impl.ContainerManagerBase;

	public class CamoSelector_carousel extends AbstractView {
		private static const NAME_MAIN:String = "main";

		public function CamoSelector_carousel() : void {
			super();
		}

		protected static function getCarousel(): * {
			var viewContainer:MainViewContainer = (App.containerMgr as ContainerManagerBase).getContainer(
				LAYER_NAMES.LAYER_ORDER.indexOf(LAYER_NAMES.VIEWS)) as MainViewContainer;
			var viewPage:LobbyPage = viewContainer.getChildByName(NAME_MAIN) as LobbyPage;
			var bottomPanel:* = viewPage.getSubContainers()[0].getTopmostView().bottomPanel;
			return bottomPanel.carousel;
		}

		override protected function onPopulate():void {
			super.onPopulate();

			try {
				parent.removeChild(this);
				var viewContainer:MainViewContainer = (App.containerMgr as ContainerManagerBase).getContainer(
					LAYER_NAMES.LAYER_ORDER.indexOf(LAYER_NAMES.VIEWS)) as MainViewContainer;
				viewContainer.setFocusedView(viewContainer.getTopmostView());
				var carousel:* = CamoSelector_carousel.getCarousel();
				carousel.scrollList.addEventListener(Event.RESIZE, CamoSelector_carousel.onScrollListResizeHandler, false, -1, true);
				carousel.getDataProvider().addEventListener(Event.CHANGE, CamoSelector_carousel.onDataProviderChangeHandler, false, -1, true);
			} catch (error:Error) {
				DebugUtils.LOG_ERROR(error.getStackTrace());
			}
		}

		public function onSetCarouselData(): void {
			try {
				CamoSelector_carousel.fixLayout("CamoSelector: onSetCarouselData: layout fixer was too late");
			} catch (error:Error) {
				DebugUtils.LOG_ERROR(error.getStackTrace());
			}
		}

		public static function onScrollListResizeHandler(event: Event): void {
			try {
				CamoSelector_carousel.fixLayout("CamoSelector: onScrollListResize: layout fixer was too late");
			} catch (error:Error) {
				DebugUtils.LOG_ERROR(error.getStackTrace());
			}
		}

		public static function onDataProviderChangeHandler(event: Event): void {
			try {
				CamoSelector_carousel.fixLayout("CamoSelector: onDataProviderChange: layout fixer was too late");
			} catch (error:Error) {
				DebugUtils.LOG_ERROR(error.getStackTrace());
			}
		}

		protected static function fixLayout(lateMessage: String): void {
			var carousel:* = CamoSelector_carousel.getCarousel();
			var controller:* = carousel["_layoutController"];
			if (controller["_layoutValid"]) {
				DebugUtils.LOG_ERROR(lateMessage);
				return;
			}
			controller.generateLayout();
			if (controller["_itemLayoutSize"] == null) {
				return;
			}
			var _loc1_:int = 0;
			var _loc3_:int = controller["_scrollList"].horizontalGap;
			var _loc4_:Rectangle = null;
			var _loc5_:Rectangle = null;
			var _loc6_:uint = controller["_itemLayouts"].length;
			var _loc7_:uint = 0;
			var _loc9_:Boolean = false;
			while (_loc7_ < _loc6_) {
				_loc4_ = controller["_itemLayouts"][_loc7_];
				_loc9_ = controller["testForBookmark"](_loc7_, _loc1_);
				if (_loc9_) {
					_loc5_ = controller["_bookmarkLayouts"][_loc1_];
					_loc1_++;
					_loc5_.offset( -_loc3_ * _loc1_, 0);
				}
				_loc4_.offset( -_loc3_ * _loc1_, 0);
				_loc7_++;
			}
		}
	}
}
