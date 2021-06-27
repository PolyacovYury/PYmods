package polyacov_yury.views.lobby {
	import StorageCategoryPersonalReservesWithStrengthViewUI;
	import net.wg.infrastructure.base.AbstractView;
	import polyacov_yury.views.lobby.PersonalReserveStrengthFilterBlock;

	public class PersonalReserveStrengthFilterLib extends AbstractView {
		public var view:StorageCategoryPersonalReservesWithStrengthViewUI = null;
		public var filterBlock:PersonalReserveStrengthFilterBlock = null;

		public function PersonalReserveStrengthFilterLib() : void {
			super();
		}

		override protected function onPopulate():void {
			super.onPopulate();
			try {
				parent.removeChild(this);
			}
			catch (error:Error) {}
		}
	}
}
