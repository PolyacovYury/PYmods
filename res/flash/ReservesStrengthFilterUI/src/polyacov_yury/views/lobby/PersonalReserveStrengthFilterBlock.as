package polyacov_yury.views.lobby {
	import flash.events.Event;
	import flash.text.TextField;
	import flash.text.TextFieldAutoSize;
	import net.wg.data.constants.Linkages;
	import net.wg.gui.components.containers.HorizontalGroupLayout;
	import net.wg.gui.events.FiltersEvent;
	import net.wg.gui.lobby.components.ButtonFilters;
	import net.wg.gui.lobby.components.data.ButtonFiltersVO;
	import net.wg.gui.lobby.storage.categories.personalreserves.PersonalReserveFilterBlock;
	import scaleform.clik.constants.InvalidationType;

	public class PersonalReserveStrengthFilterBlock extends PersonalReserveFilterBlock {
		private static const INVALID_RESET:String = "invalidateResetData";
		private static const FILTERS_BUTTON_GAP:int = 7;
		private static const FILTERS_GROUP_GAP:int = 40;
		private static const FILTER_NAME_GAP:int = 7;
		public var strengthFilters:ButtonFilters = null;
		public var strengthFilterName:TextField = null;
		private var _strengthFiltersVO:ButtonFiltersVO;
		private var _resetData:int = 0;

		public function PersonalReserveStrengthFilterBlock() {
			super();
		}

		override protected function configUI(): void {
			super.configUI();
			this.setupFilter(this.strengthFilters);
			this.strengthFilterName.text = "#quests:missionDetails/vehicle/conditions/level";
			this.strengthFilterName.autoSize = TextFieldAutoSize.LEFT;
		}
		
		override protected function onDispose(): void {
			if (this._strengthFiltersVO) this._strengthFiltersVO.dispose();
			this._strengthFiltersVO = null;
			this.strengthFilterName = null;
			this.clearFilter(this.strengthFilters);
			this.strengthFilters = null;
			super.onDispose();
		}

		override protected function draw(): void {
			super.draw();
			if(this._strengthFiltersVO) {
				if(isInvalid(INVALID_RESET)) {
					this.strengthFilters.removeEventListener(FiltersEvent.FILTERS_CHANGED,this.onFilterBlockStrengthChangedHandler);
					this.strengthFilters.resetFilters(this._resetData);
					this.strengthFilters.addEventListener(FiltersEvent.FILTERS_CHANGED,this.onFilterBlockStrengthChangedHandler);
				}
				if(isInvalid(InvalidationType.DATA)) {
					this.strengthFilters.setData(this._strengthFiltersVO);
				}
				if(isInvalid(InvalidationType.SIZE)) {
					this.strengthFilters.x = this.qualityFilterName.x - FILTERS_GROUP_GAP - this.strengthFilters.width >> 0;
					this.strengthFilterName.x = this.strengthFilters.x - this.strengthFilterName.width - FILTER_NAME_GAP >> 0;
				}
			}
		}

		private function setupFilter(param1:ButtonFilters): void {
			param1.addEventListener(FiltersEvent.FILTERS_CHANGED, this.onFilterBlockStrengthChangedHandler);
			param1.addEventListener(Event.RESIZE, this.onFilterBlockResizeHandler);
			param1.layout = new HorizontalGroupLayout(FILTERS_BUTTON_GAP, false);
			param1.buttonLinkage = Linkages.BUTTON_BLACK;
		}

		private function clearFilter(param1:ButtonFilters) : void {
			param1.removeEventListener(FiltersEvent.FILTERS_CHANGED, this.onFilterBlockStrengthChangedHandler);
			param1.removeEventListener(Event.RESIZE, this.onFilterBlockResizeHandler);
			param1.dispose();
		}
      
		override public function resetFilters(param1:int): void
		{
			this._resetData = param1;
			super.resetFilters(param1);
		}

		public function setStrengthData(param0:ButtonFiltersVO): void {
			this._strengthFiltersVO = param0;
			invalidateData();
		}

		private function onFilterBlockStrengthChangedHandler(param1:FiltersEvent): void {
			var _loc2_:* = this.strengthFilters.filtersValue;
			dispatchEvent(new FiltersEvent(FiltersEvent.FILTERS_CHANGED + "_strength",_loc2_));
		}

		private function onFilterBlockResizeHandler(param1:Event): void {
			invalidateSize();
		}
	}
}