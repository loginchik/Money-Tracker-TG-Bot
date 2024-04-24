-- Current balance is equal to limit value on expense limit creation

CREATE OR REPLACE FUNCTION user_based.current_balance_to_limit()
RETURNS TRIGGER AS
$$
BEGIN
	new.current_balance = new.limit_value -
						(select sum(amount) from user_based.expense
							where user_id = new.user_id and subcategory = new.subcategory
								and event_time::timestamp >= new.current_period_start::date);
	if new.current_balance is null then
		new.current_balance = new.limit_value;
	end if;
	return new;
END
$$
LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER reset_balance
BEFORE INSERT
ON user_based.expense_limit
for each row
EXECUTE FUNCTION user_based.current_balance_to_limit();

-- Current period end auto calculation


create or replace function user_based.set_current_period_end()
returns trigger as
$$
begin
	new.current_period_end =
	case when new."period" = 1
		then date_add(new."current_period_start"::date, '7 days'::interval)
	when new."period" = 2
		then
			date_add(new."current_period_start"::date, '30 days'::interval)
	when new."period" = 3
		then date_add(new."current_period_start"::date, '365 days'::interval)
	else date_add(new."current_period_start"::date, '30 days'::interval)
		end case;

	if new.end_date is not null and new.current_period_end::date > new.end_date::date then
		new.current_period_end = new.end_date;
	end if;

	return new;
end;
$$
LANGUAGE plpgsql;


create or replace trigger set_period_end_on_creation
before insert on user_based.expense_limit
for each row
execute function user_based.set_current_period_end();


create or replace trigger update_period_end
before update of current_period_start on user_based.expense_limit
for each row
execute function user_based.set_current_period_end();

-- Update current balance on new expense record

create or replace function update_balance_on_new_expense()
returns trigger as
$$
begin
	update user_based.expense_limit set current_balance = current_balance - new."amount"
	where user_id = new.user_id
	and subcategory = new.subcategory
	and current_period_start <= now() and current_period_end >= now();
	return null;
end
$$
LANGUAGE plpgsql;


create or replace trigger update_limit_balance
after insert on user_based.expense
for each row
execute function update_balance_on_new_expense();
