CREATE OR REPLACE TRIGGER update_limit_balance
AFTER INSERT ON user_based.expense
FOR EACH ROW
EXECUTE FUNCTION user_based.update_balance_on_new_expense();
