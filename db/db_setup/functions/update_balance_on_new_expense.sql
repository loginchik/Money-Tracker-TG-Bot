CREATE OR REPLACE FUNCTION user_based.update_balance_on_new_expense()
RETURNS TRIGGER AS
$$
BEGIN
	UPDATE user_based.expense_limit SET current_balance = current_balance - NEW."amount"
	WHERE user_id = NEW.user_id
	AND subcategory = NEW.subcategory
	AND current_period_start <= now();
	RETURN NULL;
END
$$
LANGUAGE plpgsql;
