import { Command, CommandOptions } from '@sapphire/framework';
import { ApplyOptions } from '@util/utils';
import { Message, TextChannel } from 'discord.js';

@ApplyOptions<CommandOptions>({
	aliases: ['players', 'pl'],
	description: 'Shows the playerlist of an ongoing game.',
	preconditions: ['GuildOnly', 'GameOnly']
})
export default class extends Command {

	public run(msg: Message) {
		const { game } = msg.channel as TextChannel;
		return msg.channel.send(game!.players.show());
	}

}
