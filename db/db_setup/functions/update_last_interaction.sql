create or replace function shared.update_last_interaction()
returns trigger as
$$
begin
	update shared.user set last_interaction = now() where tg_id = new.user_id;
	return new;
end;
$$
language plpgsql;