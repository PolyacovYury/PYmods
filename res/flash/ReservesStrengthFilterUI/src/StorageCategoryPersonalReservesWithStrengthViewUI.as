package  {
	import net.wg.data.constants.Errors;
	import net.wg.gui.events.FiltersEvent;
	import net.wg.gui.lobby.components.data.ButtonFiltersVO;
	import net.wg.gui.lobby.storage.categories.personalreserves.StorageCategoryPersonalReservesView;
	import polyacov_yury.views.lobby.PersonalReserveStrengthFilterBlock;

	public class StorageCategoryPersonalReservesWithStrengthViewUI extends StorageCategoryPersonalReservesView {
		public var onStrengthChange:Function;

		public function StorageCategoryPersonalReservesWithStrengthViewUI() {
			super();
			this.__setProp_scrollBar_StorageCategoryPersonalReservesViewUI_scrollBar_0();
		}

		override protected function configUI(): void {
			this.filtersBlock = new PersonalReserveStrengthFilterBlock();
			super.configUI();
			this.filtersBlock.addEventListener(FiltersEvent.FILTERS_CHANGED + "_strength",this.onFiltersBlockStrengthChangedHandler);
		}

		public function as_initStrengthFilter(param1:Object): void {
			(this.filtersBlock as PersonalReserveStrengthFilterBlock).setStrengthData(new ButtonFiltersVO(param1));
		}

		private function onFiltersBlockStrengthChangedHandler(param1:FiltersEvent): void {
			onStrengthChangeS(param1.filtersValue);
		}

		public function onStrengthChangeS(param1:int): void {
			App.utils.asserter.assertNotNull(this.onStrengthChange, "onStrengthChange" + Errors.CANT_NULL);
			this.onStrengthChange(param1);
		}

		override protected function onDispose(): void {
			this.filtersBlock.removeEventListener(FiltersEvent.FILTERS_CHANGED + "_strength", this.onFiltersBlockStrengthChangedHandler);
			super.onDispose();
		}

		private function __setProp_scrollBar_StorageCategoryPersonalReservesViewUI_scrollBar_0(): * {
			try {
				scrollBar["componentInspectorSetting"] = true;
			} catch (e:Error) {}
			scrollBar.UIID = 58458164;
			scrollBar.enableInitCallback = false;
			scrollBar.minThumbSize = 20;
			scrollBar.offsetBottom = 0;
			scrollBar.offsetTop = 0;
			scrollBar.scrollTarget = "";
			scrollBar.trackMode = "scrollPage";
			scrollBar.visible = true;
			try {
				scrollBar["componentInspectorSetting"] = false;
				return;
			} catch (e:Error) {
				return;
			}
		}
	}
}