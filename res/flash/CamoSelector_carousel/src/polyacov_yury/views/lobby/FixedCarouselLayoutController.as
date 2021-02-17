package polyacov_yury.views.lobby {
	import flash.geom.Rectangle;
	import net.wg.gui.components.carousels.interfaces.IScroller;
	import net.wg.gui.lobby.vehicleCustomization.CustomizationCarouselLayoutController;

	public class FixedCarouselLayoutController extends CustomizationCarouselLayoutController {
		public function FixedCarouselLayoutController(param1:IScroller) {
			super(param1);
		}

		override public function generateLayout(): void {
			super.generateLayout();
			if (this["_itemLayoutSize"] == null) {
				return;
			}
			var _loc1_:int = 0;
			var _loc3_:int = this["_scrollList"].horizontalGap;
			var _loc4_:Rectangle = null;
			var _loc5_:Rectangle = null;
			var _loc6_:uint = this["_itemLayouts"].length;
			var _loc7_:uint = 0;
			var _loc9_:Boolean = false;
			while (_loc7_ < _loc6_) {
				_loc4_ = this["_itemLayouts"][_loc7_];
				_loc9_ = this["testForBookmark"](_loc7_, _loc1_);
				if (_loc9_) {
					_loc5_ = this["_bookmarkLayouts"][_loc1_];
					_loc1_++;
					_loc5_.offset( -_loc3_ * _loc1_, 0);
				}
				_loc4_.offset( -_loc3_ * _loc1_, 0);
				_loc7_++;
			}
		}
	}
}