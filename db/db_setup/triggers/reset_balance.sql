CREATE OR REPLACE TRIGGER reset_balance
BEFORE INSERT
ON user_based.expense_limit
FOR EACH ROW
EXECUTE FUNCTION user_based.current_balance_to_limit();