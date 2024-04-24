CREATE OR REPLACE FUNCTION user_based.current_balance_to_limit()
RETURNS TRIGGER AS
$$
BEGIN
	NEW.current_balance = NEW.limit_value -
						(SELECT sum(amount) FROM user_based.expense
							WHERE user_id = NEW.user_id AND subcategory = NEW.subcategory
								AND event_time::timestamp >= NEW.current_period_start::date);
	IF NEW.current_balance IS NULL THEN
		NEW.current_balance = NEW.limit_value;
	END IF;
	RETURN NEW;
END
$$
LANGUAGE plpgsql;