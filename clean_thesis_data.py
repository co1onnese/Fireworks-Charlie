"""
Clean thesis and position data from database for fresh start
Keeps all market data, news, fundamentals, etc. (the good data we collected)
"""
from sqlalchemy import func, delete
from data_collection.database_manager import (
    DatabaseManager, ThesisGeneration, Position,
    RLVRTrainingExample, HistoricalReturn, SharpeCalculation
)
from orchestration.config_manager import config

def clean_thesis_data():
    """Remove all thesis-related data while preserving market data"""

    db_manager = DatabaseManager(config.DB_URL)
    session = db_manager.get_session()

    print("=" * 80)
    print("CLEANING THESIS DATA FROM DATABASE")
    print("=" * 80)
    print()
    print("⚠️  This will DELETE all:")
    print("   • ThesisGeneration records")
    print("   • Position records")
    print("   • RLVRTrainingExample records")
    print("   • HistoricalReturn records")
    print("   • SharpeCalculation records")
    print()
    print("✅ This will KEEP all:")
    print("   • Ticker metadata")
    print("   • MarketData (OHLCV + technical indicators)")
    print("   • Fundamentals")
    print("   • News articles")
    print("   • MacroFeatures")
    print("   • Insider transactions")
    print()

    # Count existing records
    print("📊 Current record counts:")
    thesis_count = session.query(func.count(ThesisGeneration.thesis_id)).scalar()
    position_count = session.query(func.count(Position.position_id)).scalar()
    rlvr_count = session.query(func.count(RLVRTrainingExample.example_id)).scalar()
    historical_count = session.query(func.count(HistoricalReturn.return_id)).scalar()
    sharpe_count = session.query(func.count(SharpeCalculation.sharpe_id)).scalar()

    print(f"   • ThesisGeneration: {thesis_count}")
    print(f"   • Position: {position_count}")
    print(f"   • RLVRTrainingExample: {rlvr_count}")
    print(f"   • HistoricalReturn: {historical_count}")
    print(f"   • SharpeCalculation: {sharpe_count}")
    print()

    # Ask for confirmation
    response = input("❓ Proceed with deletion? (type 'yes' to confirm): ")
    if response.lower() != 'yes':
        print("❌ Cancelled. No changes made.")
        session.close()
        return

    print()
    print("🗑️  Deleting records...")

    try:
        # Delete in correct order (respecting foreign keys)

        # 1. Delete RLVR training examples (references positions)
        deleted_rlvr = session.query(RLVRTrainingExample).delete()
        print(f"   ✅ Deleted {deleted_rlvr} RLVRTrainingExample records")

        # 2. Delete historical returns (references positions)
        deleted_historical = session.query(HistoricalReturn).delete()
        print(f"   ✅ Deleted {deleted_historical} HistoricalReturn records")

        # 3. Delete Sharpe calculations
        deleted_sharpe = session.query(SharpeCalculation).delete()
        print(f"   ✅ Deleted {deleted_sharpe} SharpeCalculation records")

        # 4. Delete positions (references theses)
        deleted_positions = session.query(Position).delete()
        print(f"   ✅ Deleted {deleted_positions} Position records")

        # 5. Delete thesis generations (base table)
        deleted_theses = session.query(ThesisGeneration).delete()
        print(f"   ✅ Deleted {deleted_theses} ThesisGeneration records")

        # Commit the transaction
        session.commit()
        print()
        print("✅ Database cleaned successfully!")
        print()
        print("💡 Next steps:")
        print("   1. Clear checkpoints: rm /opt/Fireworks-Charlie/storage/checkpoints/*")
        print("   2. Run main.py with fixed code to regenerate theses")

    except Exception as e:
        session.rollback()
        print(f"❌ Error during deletion: {e}")
        print("   Transaction rolled back. Database unchanged.")

    finally:
        session.close()

if __name__ == "__main__":
    clean_thesis_data()
