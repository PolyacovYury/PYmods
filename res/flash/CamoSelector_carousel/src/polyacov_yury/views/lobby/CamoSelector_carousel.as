package polyacov_yury.views.lobby {
	import flash.filters.DropShadowFilter;
	import flash.text.TextField;
	import net.wg.data.constants.generated.LAYER_NAMES;
	import net.wg.gui.battle.random.views.BattlePage;
	import net.wg.gui.lobby.LobbyPage;
	import net.wg.gui.components.containers.MainViewContainer;
	import net.wg.infrastructure.base.AbstractView;
	import net.wg.infrastructure.managers.impl.ContainerManagerBase;
	import net.wg.gui.lobby.vehicleCustomization.CustomizationCarousel;
	import scaleform.gfx.TextFieldEx;

	public class CamoSelector_carousel extends AbstractView {
		private static const NAME_MAIN:String = "main";

		public var py_log:Function;

		public function CamoSelector_carousel() : void {
			super();
		}

		override protected function onPopulate():void {
			super.onPopulate();

			try {
				parent.removeChild(this);
				var viewContainer:MainViewContainer = (App.containerMgr as ContainerManagerBase).getContainer(
					LAYER_NAMES.LAYER_ORDER.indexOf(LAYER_NAMES.VIEWS)) as MainViewContainer;
				viewContainer.setFocusedView(viewContainer.getTopmostView());
				var viewPage:LobbyPage = viewContainer.getChildByName(NAME_MAIN) as LobbyPage;
				var carousel:CustomizationCarousel = viewPage.getSubContainers()[0].getTopmostView().bottomPanel.carousel;
				var controller:FixedCarouselLayoutController = new FixedCarouselLayoutController(carousel.scrollList);
				carousel.scrollList.setLayoutController(controller);
				carousel["_layoutController"].dispose();
				carousel["_layoutController"] = controller;
				controller.setData(carousel["_data"]);
				carousel.invalidateData();
				carousel.invalidateSize();
			}
			catch (error:Error) {
				py_log(error.getStackTrace());
			}
		}

		override protected function onDispose():void {
			super.onDispose();
		}
	}
}
