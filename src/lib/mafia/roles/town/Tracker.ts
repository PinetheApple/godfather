import SingleTarget from '@root/lib/mafia/mixins/SingleTarget';
import Townie from '@mafia/mixins/Townie';
import NightActionsManager, { NightActionPriority } from '@mafia/managers/NightActionsManager';
import Player from '@mafia/Player';
import { listItems } from '@util/utils';

class Tracker extends SingleTarget {

	public name = 'Tracker';
	public description = 'You may track one person at night to find out who they visited.';
	public action = 'track';
	public actionText = 'track a player';
	public actionGerund = 'tracking';
	public priority = NightActionPriority.TRACKER;

	public tearDown(actions: NightActionsManager, target: Player) {
		const visited = this.game.players.filter(player => player.visitors.includes(target));
		if (visited.length > 0) {
			return this.player.user.send(`Your target visited ${listItems(visited.map(player => player.user.username))}`);
		}
	}

}

export default Townie(Tracker);