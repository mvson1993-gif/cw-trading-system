import pytest
import json
import os
from cw_trading_system.data.position_store import load_portfolio, save_portfolio, add_cw, remove_cw, remove_expired
from cw_trading_system.data.positions import CWPosition, HedgePosition


class TestPositionStore:
    def test_load_portfolio_empty(self, tmp_path):
        # Mock the repository file path
        import cw_trading_system.data.position_store as ps
        original_path = ps._position_repo.file_path
        ps._position_repo.file_path = str(tmp_path / "positions.json")
        ps._position_repo._ensure_file_exists()

        cw, hedge = load_portfolio()
        assert cw == []
        assert hedge == []
        
        # Restore original path
        ps._position_repo.file_path = original_path

    def test_save_and_load_portfolio(self, tmp_path):
        import cw_trading_system.data.position_store as ps
        original_path = ps._position_repo.file_path
        ps._position_repo.file_path = str(tmp_path / "positions.json")
        ps._position_repo._ensure_file_exists()

        cw = [CWPosition("HPG", "HPG2406", 1000, 1.0, 100, "2024-06-01", 10.0, 0.3)]
        hedge = [HedgePosition("HPG", 1000, 95.0)]

        save_portfolio(cw, hedge)
        loaded_cw, loaded_hedge = load_portfolio()

        assert len(loaded_cw) == 1
        assert loaded_cw[0].underlying == "HPG"
        assert len(loaded_hedge) == 1
        assert loaded_hedge[0].underlying == "HPG"
        
        # Restore original path
        ps._position_repo.file_path = original_path

    def test_add_cw(self, tmp_path):
        import cw_trading_system.data.position_store as ps
        # Create a test repository with tmp_path
        test_file = str(tmp_path / "positions.json")
        ps._position_repo.file_path = test_file

        cw_positions = []
        hedge_positions = []

        new_pos = CWPosition("HPG", "HPG2406", 1000, 1.0, 100, "2024-06-01", 10.0, 0.3)
        add_cw(new_pos, cw_positions, hedge_positions)

        assert len(cw_positions) == 1
        # Check file was written
        assert os.path.exists(test_file)

    def test_remove_cw_valid(self, tmp_path):
        import cw_trading_system.data.position_store as ps
        original_path = ps._position_repo.file_path
        ps._position_repo.file_path = str(tmp_path / "positions.json")
        ps._position_repo._ensure_file_exists()

        cw_positions = [CWPosition("HPG", "HPG2406", 1000, 1.0, 100, "2024-06-01", 10.0, 0.3)]
        hedge_positions = []

        remove_cw(0, cw_positions, hedge_positions)
        assert len(cw_positions) == 0
        
        ps._position_repo.file_path = original_path

    def test_remove_cw_invalid_index(self, tmp_path):
        import cw_trading_system.data.position_store as ps
        original_path = ps._position_repo.file_path
        ps._position_repo.file_path = str(tmp_path / "positions.json")
        ps._position_repo._ensure_file_exists()

        cw_positions = [CWPosition("HPG", "HPG2406", 1000, 1.0, 100, "2024-06-01", 10.0, 0.3)]
        hedge_positions = []

        remove_cw(5, cw_positions, hedge_positions)  # Invalid index
        assert len(cw_positions) == 1  # Should remain
        
        ps._position_repo.file_path = original_path

    def test_remove_expired(self, tmp_path):
        import cw_trading_system.data.position_store as ps
        original_path = ps._position_repo.file_path
        ps._position_repo.file_path = str(tmp_path / "positions.json")
        ps._position_repo._ensure_file_exists()

        cw_positions = [
            CWPosition("HPG", "HPG2606", 1000, 1.0, 100, "2026-06-01", 10.0, 0.3),  # Future
            CWPosition("MWG", "MWG2000", 500, 1.0, 150, "2000-01-01", 15.0, 0.35)   # Expired
        ]
        hedge_positions = []

        result = remove_expired(cw_positions, hedge_positions)
        assert len(result) == 1
        assert result[0].underlying == "HPG"
        
        ps._position_repo.file_path = original_path